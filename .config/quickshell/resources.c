// SPDX-License-Identifier: GPL-3.0-or-later
// Linux resource counters for the Quickshell bar and monitor. Emit one JSON object per line.
#define _GNU_SOURCE
#include <glib.h>
#include <glob.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/statvfs.h>
#include <unistd.h>

#ifndef PROC_ROOT
#define PROC_ROOT "/proc"
#endif
#ifndef SYS_ROOT
#define SYS_ROOT "/sys"
#endif

static char *read_file(const char *path) {
    char *text = NULL;
    if (!g_file_get_contents(path, &text, NULL, NULL)) return NULL;
    return g_strchomp(text);
}

static char *read_child(const char *dir, const char *name) {
    g_autofree char *path = g_build_filename(dir, name, NULL);
    return read_file(path);
}

static double number(const char *text, double limit) {
    if (!text) return NAN;
    char *end;
    double n = g_ascii_strtod(text, &end);
    return end != text && !*end && isfinite(n) && n >= 0 && n <= limit ? n : NAN;
}

static double sensor_value(const char *path) {
    g_autofree char *raw = read_file(path);
    double value = number(raw, 149999) / 1000;
    return value > 0 ? value : NAN;
}

static void json_number(double n) {
    if (isfinite(n)) printf("%.3f", n);
    else fputs("null", stdout);
}

static void json_string(const char *text) {
    g_autofree char *valid = g_utf8_make_valid(text, -1);
    putchar('"');
    for (const unsigned char *p = (unsigned char *)valid; *p; ++p) {
        if (*p < 32) printf("\\u%04x", (unsigned)*p);
        else {
            if (*p == '"' || *p == '\\') putchar('\\');
            putchar(*p);
        }
    }
    putchar('"');
}

typedef struct { double total, idle; int package, core; } Cpu;
typedef struct { guint id; double usage; } Thread;
typedef struct { int package, core; double total, idle, temperature; GArray *threads; } Core;

static int topology_id(int cpu, const char *field) {
    g_autofree char *path = g_strdup_printf(SYS_ROOT "/devices/system/cpu/cpu%d/topology/%s", cpu, field);
    g_autofree char *text = read_file(path);
    double n = number(text, G_MAXINT);
    return isfinite(n) ? (int)n : -1;
}

// Slot 0 holds the machine total. Logical CPU n occupies slot n+1.
static GArray *cpu_times(GArray *previous, gboolean detail) {
    GArray *times = g_array_new(FALSE, TRUE, sizeof(Cpu));
    FILE *f = fopen(PROC_ROOT "/stat", "r");
    if (!f) return times;
    char *line = NULL;
    size_t length = 0;
    while (getline(&line, &length, f) >= 0 && g_str_has_prefix(line, "cpu")) {
        char *fields = strchr(line, ' ');
        if (!fields) continue;
        *fields++ = 0;
        int id = !strcmp(line, "cpu") ? -1 : (int)g_ascii_strtoll(line + 3, NULL, 10);
        if (id >= 0 && !detail) break;
        double ticks[8] = {0};
        if (sscanf(fields, "%lf %lf %lf %lf %lf %lf %lf %lf", &ticks[0], &ticks[1], &ticks[2],
                   &ticks[3], &ticks[4], &ticks[5], &ticks[6], &ticks[7]) < 4) continue;
        guint slot = id + 1;
        if (times->len <= slot) g_array_set_size(times, slot + 1);
        Cpu *cpu = &g_array_index(times, Cpu, slot);
        for (size_t i = 0; i < G_N_ELEMENTS(ticks); ++i) cpu->total += ticks[i];
        cpu->idle = ticks[3] + ticks[4];
        if (id >= 0) {
            if (previous && previous->len > slot && g_array_index(previous, Cpu, slot).total > 0) {
                Cpu old = g_array_index(previous, Cpu, slot);
                cpu->package = old.package;
                cpu->core = old.core;
            } else {
                cpu->package = topology_id(id, "physical_package_id");
                cpu->core = topology_id(id, "core_id");
                if (cpu->package < 0 || cpu->core < 0) {
                    cpu->package = -1;
                    cpu->core = id;
                }
            }
        }
    }
    free(line);
    fclose(f);
    return times;
}

static double percent(double total, double idle) {
    return total > 0 ? CLAMP(100 * (total - idle) / total, 0, 100) : NAN;
}

static GArray *core_usage(GArray *prev, GArray *now) {
    GArray *cores = g_array_new(FALSE, FALSE, sizeof(Core));
    for (guint i = 1; i < now->len; ++i) {
        Cpu cpu = g_array_index(now, Cpu, i);
        if (!cpu.total) continue;
        guint j = 0;
        while (j < cores->len) {
            Core core = g_array_index(cores, Core, j);
            if (core.package == cpu.package && core.core == cpu.core) break;
            ++j;
        }
        if (j == cores->len) {
            Core core = {.package = cpu.package, .core = cpu.core, .temperature = NAN,
                         .threads = g_array_new(FALSE, FALSE, sizeof(Thread))};
            g_array_append_val(cores, core);
        }
        Core *core = &g_array_index(cores, Core, j);
        Thread thread = {.id = i - 1, .usage = NAN};
        if (i < prev->len) {
            Cpu old = g_array_index(prev, Cpu, i);
            if (old.total && cpu.total >= old.total) {
                double total = cpu.total - old.total, idle = cpu.idle - old.idle;
                thread.usage = percent(total, idle);
                core->total += total;
                core->idle += idle;
            }
        }
        g_array_append_val(core->threads, thread);
    }
    return cores;
}

typedef struct { double cpu, gpu, storage, chipset, package; } Thermal;

static Thermal temperatures(GArray *cores) {
    Thermal t = {NAN, NAN, NAN, NAN, NAN};
    glob_t devices = {0};
    glob(SYS_ROOT "/class/hwmon/hwmon*", 0, NULL, &devices);
    for (size_t i = 0; i < devices.gl_pathc; ++i) {
        const char *dir = devices.gl_pathv[i];
        g_autofree char *name = read_child(dir, "name");
        if (!name) continue;
        double *target;
        if (g_strv_contains((const char *[]){"coretemp","k10temp","zenpower","cpu_thermal",NULL}, name)) target = &t.cpu;
        else if (cores) continue; // The always-on sampler only needs CPU sensors.
        else if (g_strv_contains((const char *[]){"amdgpu","nouveau","i915","xe",NULL}, name)) target = &t.gpu;
        else if (!strcmp(name,"nvme") || !strcmp(name,"drivetemp")) target = &t.storage;
        else if (g_str_has_prefix(name, "pch_")) target = &t.chipset;
        else continue;

        glob_t sensors = {0};
        g_autofree char *pattern = g_build_filename(dir, "temp*_input", NULL);
        glob(pattern, 0, NULL, &sensors);
        double highest = NAN, composite = NAN;
        gboolean has_composite = FALSE;
        int package = -1;
        g_autoptr(GArray) core_sensors = g_array_new(FALSE, FALSE, sizeof(Core));
        for (size_t j = 0; j < sensors.gl_pathc; ++j) {
            const char *path = sensors.gl_pathv[j];
            g_autofree char *label_path = g_strdup(path);
            strcpy(label_path + strlen(path) - 5, "label");
            g_autofree char *label = read_file(label_path);
            double value = sensor_value(path);
            highest = fmax(highest, value);
            if (!g_strcmp0(label, "Composite")) {
                has_composite = TRUE;
                composite = fmax(composite, value);
            }
            if (cores && label) {
                int id;
                if (sscanf(label, "Package id %d", &id) == 1) package = id;
                if (!strcmp(name, "coretemp") && sscanf(label, "Core %d", &id) == 1) {
                    Core sensor = {.core = id, .temperature = value};
                    g_array_append_val(core_sensors, sensor);
                    continue;
                }
            }
            if (target == &t.cpu) t.package = fmax(t.package, value);
        }
        *target = fmax(*target, !strcmp(name, "nvme") && has_composite ? composite : highest);
        if (cores && package >= 0) {
            for (guint j = 0; j < cores->len; ++j) {
                Core *c = &g_array_index(cores, Core, j);
                if (c->package != package) continue;
                for (guint k = 0; k < core_sensors->len; ++k) {
                    Core s = g_array_index(core_sensors, Core, k);
                    if (c->core == s.core) c->temperature = s.temperature;
                }
            }
        }
        globfree(&sensors);
    }
    globfree(&devices);
    return t;
}

typedef struct { double total, used, percent, swap, swap_used; } Memory;

static Memory memory_stats(void) {
    Memory m = {0};
    FILE *f = fopen(PROC_ROOT "/meminfo", "r");
    if (!f) return m;
    char line[256], key[64];
    double kb, available = NAN, free_mem = 0, free_swap = 0;
    while (fgets(line, sizeof line, f)) {
        if (sscanf(line, "%63[^:]: %lf", key, &kb) != 2) continue;
        double bytes = kb * 1024;
        if (!strcmp(key, "MemTotal")) m.total = bytes;
        else if (!strcmp(key, "MemAvailable")) available = bytes;
        else if (!strcmp(key, "MemFree")) free_mem = bytes;
        else if (!strcmp(key, "SwapTotal")) m.swap = bytes;
        else if (!strcmp(key, "SwapFree")) free_swap = bytes;
    }
    fclose(f);
    m.used = m.total - (isfinite(available) ? available : free_mem);
    m.percent = m.total ? 100 * m.used / m.total : NAN;
    m.swap_used = m.swap - free_swap;
    return m;
}

static void summary(GArray *prev, GArray *now, Memory mem) {
    g_autoptr(GArray) cores = core_usage(prev, now);
    Thermal t = temperatures(cores);
    printf(",\"ram\":%.2f,\"cpuSensor\":", mem.percent);
    json_number(t.package);
    fputs(",\"cores\":[", stdout);
    int first_package = -1;
    gboolean multi = FALSE;
    for (guint j = 0; j < cores->len; ++j) {
        int package = g_array_index(cores, Core, j).package;
        if (package < 0) continue;
        if (first_package < 0) first_package = package;
        else if (package != first_package) multi = TRUE;
    }
    for (guint j = 0; j < cores->len; ++j) {
        Core c = g_array_index(cores, Core, j);
        if (j) putchar(',');
        fputs("{\"label\":\"", stdout);
        if (multi && c.package >= 0) printf("Socket %d · ", c.package);
        printf("%s %d\",\"usage\":", c.package < 0 ? "CPU" : "Core", c.core);
        json_number(percent(c.total, c.idle));
        fputs(",\"temperature\":", stdout);
        json_number(c.temperature);
        fputs(",\"threads\":[", stdout);
        for (guint k = 0; k < c.threads->len; ++k) {
            Thread thread = g_array_index(c.threads, Thread, k);
            if (k) putchar(',');
            printf("{\"id\":%u,\"usage\":", thread.id);
            json_number(thread.usage);
            putchar('}');
        }
        fputs("]}", stdout);
        g_array_unref(c.threads);
    }
    putchar(']');
}

static void gpu_row(gboolean *first, const char *id, const char *name, double usage,
                    double used, double total, double temp, Thermal *thermal) {
    if (!*first) putchar(',');
    *first = FALSE;
    fputs("{\"id\":", stdout); json_string(id);
    fputs(",\"name\":", stdout); json_string(name);
    fputs(",\"utilization\":", stdout); json_number(usage);
    fputs(",\"memoryUsed\":", stdout); json_number(used);
    fputs(",\"memoryTotal\":", stdout); json_number(total);
    fputs(",\"temperature\":", stdout); json_number(temp);
    putchar('}');
    thermal->gpu = fmax(thermal->gpu, temp);
}

static void gpu_stats(Thermal *t) {
    gboolean first = TRUE;
    fputs(",\"gpus\":[", stdout);
    g_autofree char *smi = g_find_program_in_path("nvidia-smi");
    if (smi) {
        char *args[] = {"timeout", "-k", "0.2s", "1s", smi,
            "--query-gpu=pci.bus_id,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
            "--format=csv,noheader,nounits", NULL};
        g_autofree char *output = NULL;
        int status = 0;
        if (g_spawn_sync(NULL, args, NULL, G_SPAWN_SEARCH_PATH | G_SPAWN_STDERR_TO_DEV_NULL,
                         NULL, NULL, &output, NULL, &status, NULL) && status == 0) {
            g_auto(GStrv) lines = g_strsplit(output, "\n", -1);
            for (char **line = lines; *line; ++line) {
                char *name = strchr(*line, ',');
                if (!name) continue;
                *name++ = 0;
                // Only the product name can contain commas. Split numeric fields from the end.
                char *fields[4];
                int i = 3;
                for (; i >= 0; --i) {
                    char *comma = strrchr(name, ',');
                    if (!comma) break;
                    *comma = 0;
                    fields[i] = g_strstrip(comma + 1);
                }
                name = g_strstrip(name);
                size_t len = strlen(name);
                if (len >= 2 && name[0] == '"' && name[len - 1] == '"') {
                    name[len - 1] = 0;
                    ++name;
                    char *out = name;
                    for (const char *in = name; *in; ++in) {
                        if (*in == '"' && in[1] == '"') ++in;
                        *out++ = *in;
                    }
                    *out = 0;
                }
                char *bus = g_strstrip(*line);
                if (i >= 0 || !*name || !*bus) continue;
                gpu_row(&first, bus, name, number(fields[0], 100), number(fields[1], G_MAXDOUBLE) * 1048576,
                        number(fields[2], G_MAXDOUBLE) * 1048576, number(fields[3], 150), t);
            }
        }
    }
    glob_t cards = {0};
    glob(SYS_ROOT "/class/drm/card[0-9]*/device", 0, NULL, &cards);
    for (size_t i = 0; i < cards.gl_pathc; ++i) {
        const char *dir = cards.gl_pathv[i];
        g_autofree char *parent = g_path_get_dirname(dir);
        g_autofree char *card = g_path_get_basename(parent);
        if (strspn(card + 4, "0123456789") != strlen(card + 4)) continue;
        g_autofree char *vendor = read_child(dir, "vendor");
        if (g_strcmp0(vendor, "0x1002")) continue;
        g_autofree char *name = read_child(dir, "product_name");
        g_autofree char *usage = read_child(dir, "gpu_busy_percent");
        g_autofree char *used = read_child(dir, "mem_info_vram_used");
        g_autofree char *total = read_child(dir, "mem_info_vram_total");
        g_autofree char *pattern = g_build_filename(dir, "hwmon/hwmon*/temp1_input", NULL);
        glob_t sensors = {0};
        glob(pattern, 0, NULL, &sensors);
        double temp = NAN;
        for (size_t j = 0; j < sensors.gl_pathc; ++j)
            temp = fmax(temp, sensor_value(sensors.gl_pathv[j]));
        globfree(&sensors);
        g_autofree char *id = realpath(dir, NULL);
        gpu_row(&first, id ? id : dir, name ? name : "AMD GPU", number(usage, 100),
                number(used, G_MAXDOUBLE), number(total, G_MAXDOUBLE), temp, t);
    }
    globfree(&cards);
    putchar(']');
}

typedef struct { double rx, tx; } Net;

static GHashTable *network(void) {
    GHashTable *table = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, g_free);
    FILE *f = fopen(PROC_ROOT "/net/dev", "r");
    if (!f) return table;
    char line[1024];
    while (fgets(line, sizeof line, f)) {
        char *fields = strrchr(line, ':');
        if (!fields) continue;
        *fields++ = 0;
        char *name = g_strstrip(line);
        Net net;
        if (!strcmp(name, "lo") ||
            sscanf(fields, "%lf %*s %*s %*s %*s %*s %*s %*s %lf", &net.rx, &net.tx) != 2) continue;
        g_hash_table_insert(table, g_strdup(name), g_memdup2(&net, sizeof net));
    }
    fclose(f);
    return table;
}

static void network_rates(GHashTable **previous, double elapsed) {
    GHashTable *now = network();
    GList *names = g_hash_table_get_keys(now);
    names = g_list_sort(names, (GCompareFunc)g_strcmp0);
    double rx = 0, tx = 0;
    fputs(",\"interfaces\":[", stdout);
    for (GList *p = names; p; p = p->next) {
        if (p != names) putchar(',');
        json_string(p->data);
        Net *current = g_hash_table_lookup(now, p->data), *old = g_hash_table_lookup(*previous, p->data);
        if (!old) continue;
        rx += fmax(0, current->rx - old->rx) / elapsed;
        tx += fmax(0, current->tx - old->tx) / elapsed;
    }
    printf("],\"rx\":%.2f,\"tx\":%.2f", rx, tx);
    g_list_free(names);
    g_hash_table_unref(*previous);
    *previous = now;
}

typedef struct { guint64 start, ticks; } ProcessTime;
typedef struct { int pid; char *name; double cpu, memory; } ProcessRow;

static int by_activity(gconstpointer a, gconstpointer b) {
    const ProcessRow *x = a, *y = b;
    if (x->cpu != y->cpu) return x->cpu < y->cpu ? 1 : -1;
    return (x->memory < y->memory) - (x->memory > y->memory);
}

static void processes(GHashTable **previous, double elapsed) {
    GHashTable *times = g_hash_table_new_full(g_direct_hash, g_direct_equal, NULL, g_free);
    g_autoptr(GArray) rows = g_array_new(FALSE, FALSE, sizeof(ProcessRow));
    g_autoptr(GDir) proc = g_dir_open(PROC_ROOT, 0, NULL);
    const double ticks = sysconf(_SC_CLK_TCK), page = sysconf(_SC_PAGESIZE);
    const char *entry;
    while (proc && (entry = g_dir_read_name(proc))) {
        if (!g_ascii_isdigit(*entry)) continue;
        int pid = atoi(entry);
        g_autofree char *path = g_build_filename(PROC_ROOT, entry, "stat", NULL);
        g_autofree char *stat = read_file(path);
        if (!stat) continue;
        char *name = strchr(stat, '('), *end = strrchr(stat, ')');
        if (!name || !end || end <= name || end[1] != ' ') continue;
        *end = 0;
        g_auto(GStrv) fields = g_strsplit(end + 2, " ", 23);
        if (g_strv_length(fields) < 22) continue;
        ProcessTime t = {g_ascii_strtoull(fields[19], NULL, 10),
                         g_ascii_strtoull(fields[11], NULL, 10) + g_ascii_strtoull(fields[12], NULL, 10)};
        ProcessTime *old = g_hash_table_lookup(*previous, GINT_TO_POINTER(pid));
        double cpu = old && old->start == t.start && t.ticks >= old->ticks ?
                     100 * (t.ticks - old->ticks) / ticks / elapsed : 0;
        ProcessRow row = {pid, g_strdup(name + 1), cpu, page * g_ascii_strtoull(fields[21], NULL, 10)};
        g_array_append_val(rows, row);
        g_hash_table_insert(times, GINT_TO_POINTER(pid), g_memdup2(&t, sizeof t));
    }
    g_array_sort(rows, by_activity);
    fputs(",\"processes\":[", stdout);
    for (guint i = 0; i < rows->len; ++i) {
        ProcessRow row = g_array_index(rows, ProcessRow, i);
        if (i < 7) {
            if (i) putchar(',');
            printf("{\"pid\":%d,\"cpu\":%.1f,\"memory\":%.0f,\"name\":", row.pid, row.cpu, row.memory);
            json_string(row.name);
            putchar('}');
        }
        g_free(row.name);
    }
    putchar(']');
    g_hash_table_unref(*previous);
    *previous = times;
}

static void full_snapshot(Memory m, GHashTable **net, GHashTable **procs, double elapsed) {
    printf(",\"cores\":%ld,\"memory\":{\"total\":%.0f,\"used\":%.0f,\"percent\":%.2f,"
           "\"swapTotal\":%.0f,\"swapUsed\":%.0f}", sysconf(_SC_NPROCESSORS_ONLN),
           m.total, m.used, m.percent, m.swap, m.swap_used);
    struct statvfs fs = {0};
    statvfs("/", &fs);
    double size = (double)fs.f_blocks * fs.f_frsize, used = size - (double)fs.f_bfree * fs.f_frsize;
    printf(",\"disk\":{\"total\":%.0f,\"used\":%.0f,\"percent\":%.2f}", size, used, size ? 100 * used / size : 0);
    network_rates(net, elapsed);
    processes(procs, elapsed);
    Thermal t = temperatures(NULL);
    gpu_stats(&t);
    fputs(",\"temperatures\":{\"cpu\":", stdout); json_number(t.cpu);
    fputs(",\"gpu\":", stdout); json_number(t.gpu);
    fputs(",\"storage\":", stdout); json_number(t.storage);
    fputs(",\"chipset\":", stdout); json_number(t.chipset);
    fputs("},\"temperature\":", stdout); json_number(t.cpu);
    g_autofree char *uptime = read_file(PROC_ROOT "/uptime");
    double load = 0;
    getloadavg(&load, 1);
    printf(",\"uptime\":%.2f,\"load\":%.2f", uptime ? g_ascii_strtod(uptime, NULL) : 0, load);
}

int main(int argc, char **argv) {
    gboolean compact = argc == 2 && !strcmp(argv[1], "--summary");
    if (argc != 1 && !compact) {
        fprintf(stderr, "Usage: %s [--summary]\n", argv[0]);
        return 2;
    }
    GArray *prev = cpu_times(NULL, compact);
    GHashTable *net = compact ? NULL : network();
    GHashTable *procs = compact ? NULL : g_hash_table_new_full(g_direct_hash, g_direct_equal, NULL, g_free);
    gint64 last = g_get_monotonic_time();
    g_usleep(200000); // Get a real delta for the first reading.
    for (;;) {
        gint64 start = g_get_monotonic_time();
        GArray *now = cpu_times(prev, compact);
        Memory mem = memory_stats();
        if (!prev->len || !now->len || !mem.total) {
            fputs("Unable to read CPU or memory counters\n", stderr);
            return 1;
        }
        Cpu a = g_array_index(prev, Cpu, 0), b = g_array_index(now, Cpu, 0);
        double usage = percent(b.total - a.total, b.idle - a.idle);
        fputs("{\"cpu\":", stdout);
        json_number(compact || isfinite(usage) ? usage : 0);
        if (compact) summary(prev, now, mem);
        else full_snapshot(mem, &net, &procs, (start - last) / (double)G_USEC_PER_SEC);
        puts("}");
        if (fflush(stdout) == EOF) return 1;
        g_array_unref(prev);
        prev = now;
        last = start;
        gint64 wait = start + 2 * G_USEC_PER_SEC - g_get_monotonic_time();
        if (wait > 0) g_usleep(wait);
    }
}

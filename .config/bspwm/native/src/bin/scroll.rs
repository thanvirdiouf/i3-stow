// SPDX-License-Identifier: GPL-3.0-or-later

use serde::{de::IgnoredAny, Deserialize};
use std::env;
use std::error::Error;
use std::fs::OpenOptions;
use std::io::{self, Read, Seek, Write};
use std::os::unix::{ffi::OsStringExt, fs::OpenOptionsExt};
use std::path::PathBuf;
use std::process::{Command, ExitCode, Stdio};

const QUIET_INTERVAL: f64 = 0.35;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct World {
    focused_monitor_id: u32,
    monitors: Vec<Monitor>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Monitor {
    id: u32,
    focused_desktop_id: u32,
    desktops: Vec<Desktop>,
}

#[derive(Deserialize)]
struct Desktop {
    id: u32,
    root: Option<Node>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Node {
    #[serde(default)]
    hidden: bool,
    client: Option<IgnoredAny>,
    first_child: Option<Box<Node>>,
    second_child: Option<Box<Node>>,
}

impl Node {
    fn occupied(&self) -> bool {
        !self.hidden
            && (self.client.is_some()
                || self.first_child.as_deref().is_some_and(Node::occupied)
                || self.second_child.as_deref().is_some_and(Node::occupied))
    }
}

#[derive(Clone, Copy)]
enum Direction {
    Next,
    Previous,
}

fn occupied_target(world: &World, direction: Direction) -> Option<u32> {
    let monitor = world
        .monitors
        .iter()
        .find(|m| m.id == world.focused_monitor_id)?;
    let desktops = &monitor.desktops;
    let current = desktops
        .iter()
        .position(|d| d.id == monitor.focused_desktop_id)?;
    let (before, after) = desktops.split_at(current);
    let after = &after[1..];
    let occupied = |desktop: &&Desktop| desktop.root.as_ref().is_some_and(Node::occupied);
    let target = match direction {
        Direction::Next => after.iter().chain(before).find(occupied),
        Direction::Previous => before.iter().rev().chain(after.iter().rev()).find(occupied),
    };
    target.map(|desktop| desktop.id)
}

fn state_path() -> PathBuf {
    let runtime = env::var_os("XDG_RUNTIME_DIR").unwrap_or_else(|| "/tmp".into());
    let mut display = env::var_os("DISPLAY")
        .unwrap_or_else(|| "default".into())
        .into_vec();
    for byte in &mut display {
        if *byte == b'/' {
            *byte = b'_';
        }
    }
    // getuid has no arguments and cannot fail.
    let uid = unsafe { libc::getuid() };
    let mut file = format!("bspwm-scroll-{uid}-").into_bytes();
    file.extend(display);
    PathBuf::from(runtime).join(std::ffi::OsString::from_vec(file))
}

fn monotonic_seconds() -> io::Result<f64> {
    let mut now = libc::timespec {
        tv_sec: 0,
        tv_nsec: 0,
    };
    // CLOCK_MONOTONIC shares an epoch across invocations and the Python fallback.
    if unsafe { libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut now) } != 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(now.tv_sec as f64 + now.tv_nsec as f64 / 1_000_000_000.0)
}

fn scroll(direction: Direction) -> Result<(), Box<dyn Error>> {
    let mut state = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .mode(0o600)
        .custom_flags(libc::O_NOFOLLOW)
        .open(state_path())?;
    state.lock()?;
    let now = monotonic_seconds()?;
    let mut previous = String::new();
    state.read_to_string(&mut previous)?;
    // Every event extends the gesture, with the same on-disk format as Python.
    state.rewind()?;
    state.set_len(0)?;
    writeln!(&mut state, "{now}")?;
    if previous
        .trim()
        .parse::<f64>()
        .is_ok_and(|time| now - time < QUIET_INTERVAL)
    {
        return Ok(());
    }

    let snapshot = Command::new("bspc").args(["wm", "-d"]).output()?;
    if !snapshot.status.success() {
        return Err(format!(
            "bspc wm -d failed: {}",
            String::from_utf8_lossy(&snapshot.stderr).trim()
        )
        .into());
    }
    let mut parser = serde_json::Deserializer::from_slice(&snapshot.stdout);
    // A long, one-sided split tree can exceed serde_json's default depth.
    parser.disable_recursion_limit();
    let world = World::deserialize(&mut parser)?;
    parser.end()?;
    if let Some(target) = occupied_target(&world, direction) {
        // Keep serialization through the focus request. A desktop disappearing
        // before focus is a normal race, so ignore bspc's exit status here.
        Command::new("bspc")
            .args(["desktop", "-f", &target.to_string()])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()?;
    }
    Ok(())
}

fn main() -> ExitCode {
    let args: Vec<_> = env::args().skip(1).collect();
    let direction = match args.as_slice() {
        [direction] if direction == "next" => Direction::Next,
        [direction] if direction == "prev" => Direction::Previous,
        _ => {
            eprintln!("Usage: scroll next|prev");
            return ExitCode::from(2);
        }
    };
    match scroll(direction) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("bspwm scroll: {error}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn world() -> World {
        serde_json::from_str(r#"{
            "focusedMonitorId": 1,
            "monitors": [
                {"id": 1, "focusedDesktopId": 4, "desktops": [
                    {"id": 2, "root": {"client": {}}},
                    {"id": 4, "root": null},
                    {"id": 5, "root": {"hidden": true, "firstChild": {"client": {}}}},
                    {"id": 6, "root": {"firstChild": {"hidden": true, "client": {}}}},
                    {"id": 8, "root": {"firstChild": {"client": null}, "secondChild": {"client": {}}}}
                ]},
                {"id": 2, "focusedDesktopId": 10, "desktops": [{"id": 10, "root": {"client": {}}}]}
            ]
        }"#).unwrap()
    }

    #[test]
    fn scrolls_from_an_empty_desktop_and_wraps_among_visible_clients() {
        let mut world = world();
        assert_eq!(occupied_target(&world, Direction::Next), Some(8));
        assert_eq!(occupied_target(&world, Direction::Previous), Some(2));
        world.monitors[0].focused_desktop_id = 8;
        assert_eq!(occupied_target(&world, Direction::Next), Some(2));
        world.monitors[0].focused_desktop_id = 2;
        assert_eq!(occupied_target(&world, Direction::Previous), Some(8));
    }

    #[test]
    fn skips_other_monitors_when_there_is_no_local_target() {
        let mut world = world();
        world.monitors[0].desktops.pop();
        world.monitors[0].focused_desktop_id = 2;
        assert_eq!(occupied_target(&world, Direction::Next), None);
        assert_eq!(occupied_target(&world, Direction::Previous), None);
    }
}

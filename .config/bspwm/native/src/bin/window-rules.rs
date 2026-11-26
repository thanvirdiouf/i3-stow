// SPDX-License-Identifier: GPL-3.0-or-later

use spectre_desktop_helpers::XDisplay;
use std::env;
use std::ffi::{c_int, c_ulong};
use std::process::ExitCode;
use std::{ptr, slice};
use x11_dl::xlib;

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
enum Title {
    Workspaces,
    SystemMonitor,
    #[default]
    Other,
}

fn consequences(class: &str, title: Title) -> &'static str {
    match title {
        Title::Workspaces => return "state=floating center=on border=off layer=above",
        Title::SystemMonitor => return "state=floating center=on border=off",
        Title::Other => (),
    }
    // Match the Python rule's case-insensitive comparisons with ASCII letters.
    let class: String = class
        .chars()
        .map(|letter| match letter {
            'İ' | 'ı' => 'i',
            'ſ' => 's',
            'K' => 'k',
            _ => letter.to_ascii_lowercase(),
        })
        .collect();
    if matches!(
        class.as_str(),
        "localsend"
            | "localsend_app"
            | "org.localsend.localsend_app"
            | "gedit"
            | "org.gnome.gedit"
            | "blueman-manager"
            | "pavucontrol"
            | "kdeconnect"
            | "org.kde.kdeconnect"
    ) || class
        .strip_prefix("kdeconnect")
        .is_some_and(|s| s.starts_with(['.', '_', '-']) && !s.contains('\n'))
        || class
            .strip_prefix("org.kde.kdeconnect")
            .is_some_and(|s| s.starts_with(['.', '-']) && !s.contains('\n'))
    {
        "state=floating center=on"
    } else {
        ""
    }
}

fn classify_title(data: &[u8], kind: xlib::Atom) -> Title {
    match data {
        b"Spectre \xc2\xb7 Workspaces" => Title::Workspaces,
        b"Spectre \xc2\xb7 System Monitor" => Title::SystemMonitor,
        b"Spectre \xb7 Workspaces" if kind == xlib::XA_STRING => Title::Workspaces,
        b"Spectre \xb7 System Monitor" if kind == xlib::XA_STRING => Title::SystemMonitor,
        _ => Title::Other,
    }
}

fn read_title(display: &XDisplay, window: xlib::Window, atom: xlib::Atom) -> Option<Title> {
    let (mut kind, mut format, mut length, mut unread) = (0, 0, 0, 0);
    let mut data = ptr::null_mut();
    // Read up to 64 bytes, enough for either exact title. Xlib owns any result
    // allocation until XFree. An absent property has type None (zero).
    let status = unsafe {
        (display.xlib.XGetWindowProperty)(
            display.as_ptr(),
            window,
            atom,
            0,
            16,
            0,
            xlib::AnyPropertyType as _,
            &mut kind,
            &mut format,
            &mut length,
            &mut unread,
            &mut data,
        )
    };
    let title = if status != 0 || kind == 0 {
        None
    } else if format == 8 && unread == 0 && !data.is_null() {
        Some(classify_title(
            unsafe { slice::from_raw_parts(data, length as usize) },
            kind,
        ))
    } else {
        Some(Title::Other)
    };
    if !data.is_null() {
        unsafe { (display.xlib.XFree)(data.cast()) };
    }
    title
}

unsafe extern "C" fn ignore_x_error(_: *mut xlib::Display, _: *mut xlib::XErrorEvent) -> c_int {
    // An application can destroy the window before the rule runs.
    0
}

fn window_title(window: xlib::Window) -> Title {
    let Ok(display) = XDisplay::open() else {
        return Title::Other;
    };
    let raw = display.as_ptr();
    let mut names = [
        c"_SPECTRE_BSPWM".as_ptr().cast_mut(),
        c"_NET_WM_NAME".as_ptr().cast_mut(),
    ];
    let mut atoms = [0; 2];
    // Both atom names live for the program's lifetime. XInternAtoms only
    // reads the names. XChangeProperty's format 32 expects native longs.
    unsafe {
        (display.xlib.XSetErrorHandler)(Some(ignore_x_error));
        if (display.xlib.XInternAtoms)(raw, names.as_mut_ptr(), 2, 0, atoms.as_mut_ptr()) == 0 {
            return Title::Other;
        }
        let marker: c_ulong = 1;
        (display.xlib.XChangeProperty)(
            raw,
            window,
            atoms[0],
            xlib::XA_CARDINAL,
            32,
            xlib::PropModeReplace,
            ptr::from_ref(&marker).cast(),
            1,
        );
    }
    read_title(&display, window, atoms[1])
        .or_else(|| read_title(&display, window, xlib::XA_WM_NAME))
        .unwrap_or_default()
}

fn main() -> ExitCode {
    let mut args = env::args_os().skip(1);
    let (Some(id), Some(class)) = (args.next(), args.next()) else {
        eprintln!("Usage: window-rules WINDOW_ID CLASS [INSTANCE CONSEQUENCES]");
        return ExitCode::from(2);
    };
    let id = id.to_string_lossy();
    let window = match id.strip_prefix("0x").or_else(|| id.strip_prefix("0X")) {
        Some(hex) => u32::from_str_radix(hex, 16),
        None => id.parse::<u32>(),
    };
    let Ok(window) = window else {
        eprintln!("Invalid X11 window ID: {id}");
        return ExitCode::from(2);
    };
    println!(
        "{}",
        consequences(&class.to_string_lossy(), window_title(window.into()))
    );
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn titles_override_class_rules() {
        assert_eq!(
            consequences(
                "kitty",
                classify_title("Spectre · Workspaces".as_bytes(), 0)
            ),
            "state=floating center=on border=off layer=above"
        );
        assert_eq!(
            consequences(
                "Gedit",
                classify_title(b"Spectre \xb7 System Monitor", xlib::XA_STRING)
            ),
            "state=floating center=on border=off"
        );
        assert_eq!(
            classify_title(b"Spectre \xc2\xb7 Workspaces Extra", 0),
            Title::Other
        );
    }

    #[test]
    fn utility_classes_match_case_insensitively_with_their_allowed_suffixes() {
        for class in [
            "Pavucontrol",
            "org.localsend.LocalSend_App",
            "KDEConnect_APP",
            "org.kde.KDEConnect.app",
            "org.gnome.Gedİt",
        ] {
            assert_eq!(
                consequences(class, Title::Other),
                "state=floating center=on"
            );
        }
        for class in [
            "kitty",
            "kdeconnector",
            "org.kde.kdeconnect_app",
            "gedit-helper",
        ] {
            assert_eq!(consequences(class, Title::Other), "");
        }
    }
}

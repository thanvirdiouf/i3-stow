// SPDX-License-Identifier: GPL-3.0-or-later

use spectre_desktop_helpers::XDisplay;
use std::process::ExitCode;
use std::thread;
use std::time::Duration;

fn held(keymap: &[u8; 32], keycode: u8) -> bool {
    keycode != 0 && keymap[usize::from(keycode / 8)] & (1 << (keycode % 8)) != 0
}

fn main() -> ExitCode {
    let display = match XDisplay::open() {
        Ok(display) => display,
        Err(error) => {
            eprintln!("Cannot observe Super keys: {error}");
            return ExitCode::FAILURE;
        }
    };
    let raw = display.as_ptr();
    // X11 KeySyms for Super_L and Super_R. A missing mapping returns zero.
    let keys =
        [0xffeb, 0xffec].map(|symbol| unsafe { (display.xlib.XKeysymToKeycode)(raw, symbol) });
    let mut keymap = [0; 32];
    loop {
        // XQueryKeymap writes 32 bytes. Query immediately in case Super was
        // released before Quickshell finished opening the window.
        unsafe { (display.xlib.XQueryKeymap)(raw, keymap.as_mut_ptr().cast()) };
        if !keys.iter().any(|&keycode| held(&keymap, keycode)) {
            println!("released");
            return ExitCode::SUCCESS;
        }
        thread::sleep(Duration::from_millis(20));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tracks_both_mapped_keys_and_ignores_an_unmapped_key() {
        let mut keymap = [0; 32];
        keymap[0] = 1;
        keymap[8] = 1;
        keymap[13] = 1 << 4;
        assert!(held(&keymap, 64));
        assert!(held(&keymap, 108));
        keymap[8] = 0;
        assert!(!held(&keymap, 64));
        assert!(held(&keymap, 108));
        assert!(!held(&keymap, 0));
    }
}

// SPDX-License-Identifier: GPL-3.0-or-later

use std::ptr::{self, NonNull};
use x11_dl::xlib::{self, Xlib};

pub struct XDisplay {
    pub xlib: Xlib,
    raw: NonNull<xlib::Display>,
}

impl XDisplay {
    pub fn open() -> Result<Self, String> {
        let xlib = Xlib::open().map_err(|error| error.to_string())?;
        // A null display name selects the X11 display from the environment.
        let raw = NonNull::new(unsafe { (xlib.XOpenDisplay)(ptr::null()) })
            .ok_or("cannot open the X11 display")?;
        Ok(Self { xlib, raw })
    }

    pub fn as_ptr(&self) -> *mut xlib::Display {
        self.raw.as_ptr()
    }
}

impl Drop for XDisplay {
    fn drop(&mut self) {
        // This connection is owned by and lives for the lifetime of XDisplay.
        unsafe { (self.xlib.XCloseDisplay)(self.raw.as_ptr()) };
    }
}

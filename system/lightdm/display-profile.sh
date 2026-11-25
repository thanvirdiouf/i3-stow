#!/bin/sh

panel=eDP-1
hdmi=HDMI-1-0

outputs=$(/usr/bin/xrandr --query) || exit 0
if ! printf '%s\n' "$outputs" | grep -q "^$hdmi "; then
    # Expose the NVIDIA outputs on Intel's primary X screen (Reverse PRIME).
    /usr/bin/xrandr --setprovideroutputsource NVIDIA-G0 modesetting || :
    outputs=$(/usr/bin/xrandr --query) || exit 0
fi

hdmi_connected=false
if printf '%s\n' "$outputs" | grep -q "^$hdmi connected "; then
    hdmi_connected=true
fi

case " $(cat /proc/cmdline) " in
    *" display_profile=hdmi "*) profile=hdmi ;;
    *) profile=dual ;;
esac

if ! printf '%s\n' "$outputs" | grep -q "^$panel connected "; then
    if "$hdmi_connected"; then
        /usr/bin/xrandr --output "$hdmi" --primary --auto --pos 0x0 || :
    fi
    exit 0
fi

if "$hdmi_connected"; then
    case "$profile" in
        hdmi)
            # Set up HDMI and switch off the panel in the same XRandR request.
            /usr/bin/xrandr --output "$hdmi" --primary --auto --pos 0x0 \
                --output "$panel" --off && exit 0
            ;;
        dual)
            /usr/bin/xrandr --output "$panel" --primary --auto --pos 0x0 \
                --output "$hdmi" --auto --right-of "$panel" && exit 0
            ;;
    esac
fi

# Keep a usable greeter if HDMI is unavailable or the requested mode fails.
# Ignore failures here so LightDM can still start on Xorg's existing layout.
/usr/bin/xrandr --output "$panel" --primary --auto --pos 0x0 || :

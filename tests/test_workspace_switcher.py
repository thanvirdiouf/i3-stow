# SPDX-License-Identifier: GPL-3.0-or-later
"""Modifier-release and workspace-preview data regression checks."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


alt = load('alt_release', '.config/quickshell/alt-release.py')
state = load('switcher_state', '.config/quickshell/bspwm-state.py')


class WorkspaceSwitcher(unittest.TestCase):
    def test_releasing_one_alt_does_not_commit_while_other_is_held(self):
        keymap = bytearray(32)
        keymap[64 // 8] |= 1 << (64 % 8)
        keymap[108 // 8] |= 1 << (108 % 8)
        self.assertTrue(alt.held(keymap, [64, 108]))
        keymap[64 // 8] = 0
        self.assertTrue(alt.held(keymap, [64, 108]))
        keymap[108 // 8] = 0
        self.assertFalse(alt.held(keymap, [64, 108]))
        self.assertFalse(alt.held(bytearray([255]) + bytearray(31), [0]))

    def test_preview_geometry_is_relative_to_monitor_and_history_tracks_recent_use(self):
        monitor = dict(id=1, name='HDMI-1', focusedDesktopId=10,
                       rectangle=dict(x=1920, y=0, width=1920, height=1080), desktops=[
                           dict(id=10, name='1', focusedNodeId=99, root=dict(id=99, client=dict(
                               className='kitty', state='floating', floatingRectangle=dict(
                                   x=2112, y=108, width=960, height=540)))),
                           dict(id=11, name='2', root=None)])
        world = dict(focusedMonitorId=1, monitors=[monitor],
                     focusHistory=[dict(desktopId=11), dict(desktopId=10)])
        result, focused = state.model(world)
        first, second = result['workspaces']
        self.assertTrue(first['focused'])
        self.assertEqual(focused, 99)
        self.assertGreater(first['recency'], second['recency'])
        self.assertEqual(first['windows'], [dict(app='kitty', x=.1, y=.1, width=.5, height=.5)])
        self.assertFalse(second['occupied'])


if __name__ == '__main__':
    unittest.main()

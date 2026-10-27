# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rules = load('bspwm_rules', '.config/bspwm/rules.py')
state = load('bspwm_state', '.config/quickshell/bspwm-state.py')
actions = load('bspwm_actions', '.config/bspwm/actions.py')


class BspwmExperience(unittest.TestCase):
    def test_utility_matching_and_monitor_decoration(self):
        for name in ('Pavucontrol', 'org.localsend.localsend_app', 'org.kde.kdeconnect.app'):
            self.assertEqual(rules.consequences(name, 'Settings'), 'state=floating center=on')
        self.assertEqual(rules.consequences('kitty', 'Terminal'), '')
        self.assertIn('border=off', rules.consequences('', 'Spectre · System Monitor'))

    def test_bar_tracks_visible_desktops_per_monitor_and_urgent_leaves(self):
        world = dict(focusedMonitorId=1, monitors=[
            dict(id=1, name='eDP-1', focusedDesktopId=10, desktops=[
                dict(id=10, name='1', focusedNodeId=99, root=dict(client=dict(urgent=True), id=99)),
                dict(id=11, name='2', root=None)]),
            dict(id=2, name='HDMI-1', focusedDesktopId=20, desktops=[
                dict(id=20, name='work', focusedNodeId=88, root=dict(client={}, id=88))])])
        result, focused = state.model(world)
        self.assertEqual(focused, 99)
        self.assertTrue(result['workspaces'][0]['urgent'])
        self.assertFalse(result['workspaces'][1]['occupied'])
        self.assertTrue(result['workspaces'][2]['active'])
        self.assertEqual(result['workspaces'][2]['number'], -1)

    def test_desktop_reload_preserves_existing_windows_and_names(self):
        import json
        world = dict(monitors=[dict(id=1, desktops=[dict(id=10, name='1', root={'client': {}}),
                                                   dict(id=11, name='work', root=None)])])
        with patch.object(actions, 'bsp', return_value=json.dumps(world)) as bsp:
            actions.desktops()
        mutations = [call.args for call in bsp.call_args_list if call.args[0] != 'wm']
        self.assertEqual(len(mutations), 9)
        self.assertTrue(all(args[:3] == ('monitor', '1', '-a') for args in mutations))
        self.assertFalse(any('-r' in args or '-d' in args for args in mutations))

    def test_hotplug_reuses_empty_number_without_moving_live_windows(self):
        import json
        numbered = [dict(id=10 + n, name=str(n), root=None if n in (4, 10) else {'id': n})
                    for n in range(1, 11)]
        world = dict(monitors=[dict(id=1, desktops=numbered),
                               dict(id=2, desktops=[dict(id=99, name='Desktop', root=None)])])
        with patch.object(actions, 'bsp', return_value=json.dumps(world)) as bsp:
            actions.desktops()
        mutations = [call.args for call in bsp.call_args_list if call.args[0] != 'wm']
        self.assertEqual(mutations, [('desktop', '20', '-r'), ('desktop', '99', '-n', '10')])

    def test_occupied_default_keeps_its_tree_when_all_numbers_are_busy(self):
        import json
        numbered = [dict(id=10 + n, name=str(n), root={'id': n}) for n in range(1, 11)]
        world = dict(monitors=[dict(id=1, desktops=numbered),
                               dict(id=2, desktops=[dict(id=99, name='Desktop', root={'id': 123})])])
        with patch.object(actions, 'bsp', return_value=json.dumps(world)) as bsp:
            actions.desktops()
        mutations = [call.args for call in bsp.call_args_list if call.args[0] != 'wm']
        self.assertEqual(mutations, [('desktop', '99', '-n', '11')])


if __name__ == '__main__':
    unittest.main()

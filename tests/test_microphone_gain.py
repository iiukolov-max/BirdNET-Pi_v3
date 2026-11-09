import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import prepare_microphone as microphone


DEVICES = ('card 1: USB [USB microphone], device 0: USB Audio [USB Audio]\n'
           'card 1: USB [USB microphone], device 1: USB Audio [USB Audio]\n'
           'card 2: Other [Other microphone], device 0: USB Audio [USB Audio]\n')


class MicrophoneGainTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.config = Path(folder.name) / 'birdnet.conf'
        config_patch = patch.object(microphone, 'CONFIG', self.config)
        config_patch.start()
        self.addCleanup(config_patch.stop)

    def invoke(self, *args):
        with patch.object(sys, 'argv', ['prepare_microphone.py', *args]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return microphone.main()

    def test_off_missing_invalid_and_unreadable_configuration_never_changes_gain(self):
        for value in (None, '', 'MICROPHONE_GAIN_100=0\n', 'MICROPHONE_GAIN_100=yes\n',
                      'MICROPHONE_GAIN_100=$(touch unsafe)\n', 'MICROPHONE_GAIN_100="1\n'):
            with self.subTest(value=value):
                if value is not None:
                    self.config.write_text(value)
                with patch.object(microphone, 'run') as run:
                    self.assertEqual(self.invoke('--apply-gain'), 0)
                    run.assert_not_called()

    def test_boot_reads_setting_each_time_and_adjusts_every_card_once(self):
        for value, expected in [('1', 2), ('0', 0), ('"1" # enabled', 2)]:
            self.config.write_text('MICROPHONE_GAIN_100=' + value + '\n')
            with patch.object(microphone, 'run', return_value=(0, DEVICES, '')), \
                    patch.object(microphone, 'maximise_capture') as gain:
                self.assertEqual(self.invoke('--apply-gain'), 0)
                self.assertEqual(gain.call_count, expected)
                if expected:
                    self.assertEqual([c.args[0] for c in gain.call_args_list], ['USB', 'Other'])

    def test_missing_microphone_does_not_fail_boot_but_recording_retries(self):
        self.config.write_text('MICROPHONE_GAIN_100=1\n')
        with patch.object(microphone, 'run', return_value=(0, '', 'no soundcards')), \
                patch.object(microphone.time, 'sleep'), patch.object(microphone, 'maximise_capture') as gain:
            self.assertEqual(self.invoke('--apply-gain'), 0)
            self.assertEqual(self.invoke('--device', 'default'), 1)
            gain.assert_not_called()

    def test_local_recording_off_preserves_mixer_on_applies_all_cards(self):
        for enabled in ('0', '1'):
            self.config.write_text('MICROPHONE_GAIN_100=' + enabled + '\n')
            with patch.object(microphone, 'run', return_value=(0, DEVICES, '')), \
                    patch.object(microphone, 'maximise_capture') as gain, \
                    patch.object(microphone, 'release_idle_pulse_source'):
                self.assertEqual(self.invoke('--device', 'plughw:CARD=USB,DEV=0'), 0)
                self.assertEqual(gain.call_count, 2 if enabled == '1' else 0)

    def test_custom_pcm_remains_usable_with_option_on_or_off(self):
        for enabled in ('0', '1'):
            self.config.write_text('MICROPHONE_GAIN_100=' + enabled + '\n')
            with patch.object(microphone, 'run', return_value=(0, DEVICES, '')), \
                    patch.object(microphone, 'maximise_capture') as gain:
                self.assertEqual(self.invoke('--device', 'custom'), 0)
                self.assertEqual(gain.call_count, 2 if enabled == '1' else 0)

    def test_pulse_volume_and_mute_are_only_written_when_enabled(self):
        source = 'alsa_input.usb'
        sources = json.dumps([{'name': source, 'properties': {'alsa.card': '1'}}])
        for enabled in (False, True):
            def run(args, **kwargs):
                return (0, sources if '--format=json' in args else '', '')
            with patch.object(microphone, 'run', side_effect=run) as command, \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertTrue(microphone.select_pulse_source({'number': 1}, maximise=enabled))
                mutations = [c.args[0][1] for c in command.call_args_list]
                self.assertEqual('set-source-volume' in mutations, enabled)
                self.assertEqual('set-source-mute' in mutations, enabled)

    def test_playback_controls_preserved_and_shared_control_explicitly_capture(self):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if args[-1] == 'scontrols':
                return 0, "Simple mixer control 'Master',0\nSimple mixer control 'Mic',0\n", ''
            if 'sget' in args:
                return 0, ('Capabilities: pvolume pswitch\n' if args[-1] == 'Master,0'
                           else 'Capabilities: pvolume cvolume pswitch cswitch\n'), ''
            return 0, 'Front Left: Capture 100% [on]', ''
        with patch.object(microphone, 'run', side_effect=run), contextlib.redirect_stderr(io.StringIO()):
            microphone.maximise_capture('USB')
        self.assertEqual([c for c in calls if 'sset' in c],
                         [['amixer', '-c', 'USB', 'sset', 'Mic,0', 'capture', '100%', 'cap']])


if __name__ == '__main__':
    unittest.main()

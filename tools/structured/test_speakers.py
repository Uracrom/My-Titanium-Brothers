#!/usr/bin/env python3
"""Speaker-boundary cases that do not require the full archive."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from build import classify_line, parse_segments  # noqa: E402


def speakers(texts, collection='claude', verified=True):
    msgs, _segs, _flags = parse_segments(texts, collection, verified)
    return msgs


class SpeakerRules(unittest.TestCase):
    def test_prose_mentions_are_not_boundaries(self):
        msgs = speakers([
            'Alex\n\n'
            'Olá Luciana, Carla e Ana Paula. I asked Copilot about the weather, but this sentence is still mine.\n'
            'Constant attention is not a speaker.\n\n'
            'Copilot\n\n'
            'Resposta.\n'
        ], 'grok')
        self.assertEqual([m['spk'] for m in msgs], ['ALEX', 'COPILOT'])
        alex = '\n'.join(msgs[0]['parts'][0]['lines'])
        self.assertIn('Luciana, Carla e Ana Paula', alex)
        self.assertIn('I asked Copilot about the weather', alex)
        self.assertNotIn('Resposta.', alex)
        self.assertIsNone(classify_line('Luciana'))
        self.assertIsNone(classify_line('Carla'))
        self.assertIsNone(classify_line('Ana Paula'))

    def test_unlabeled_text_is_not_assigned_to_alex(self):
        msgs = speakers(['Esta frase não tem rótulo. Luciana está aqui.\n'])
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]['spk'], 'UNKNOWN')
        self.assertEqual(msgs[0]['embed_status'], 'UNLABELED')

    def test_copied_transcript_stays_mixed_inside_the_turn(self):
        msgs = speakers([
            'Alex\n\n'
            'Here is the transcript.\n\n'
            'You said:\n\n'
            'Hello from the paste.\n\n'
            'Copilot said:\n\n'
            'Reply from the paste.\n'
        ], 'grok')
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]['spk'], 'ALEX')
        regions = msgs[0]['parts'][0]['emb']
        self.assertEqual(len(regions), 1)
        self.assertTrue(regions[0][2].startswith('MIXED'))
        self.assertIn('You said:', msgs[0]['parts'][0]['lines'][regions[0][0]])

    def test_continuation_does_not_inherit_alex_from_another_ai(self):
        first = "Alex\n\nBut you wrote only the last text. There's more before that, no?\n"
        second = 'Copilot\n\nYou’re right — there is more.\n'
        msgs = speakers([first, second])
        self.assertEqual(msgs[0]['spk'], 'ALEX')
        self.assertEqual(len(msgs[0]['parts']), 1)
        self.assertEqual(msgs[1]['spk'], 'COPILOT')
        self.assertEqual(msgs[1]['parts'][0]['seg'], 1)
        self.assertNotIn('You’re right', '\n'.join(msgs[0]['parts'][0]['lines']))

    def test_broader_labels_and_source_lines(self):
        msgs = speakers([
            'Alex\n\n'
            'Vertex\n\nHello from Vertex.\n\n'
            '(Prism responding:)\n\nHello from Prism.\n\n'
            'From Grok\n\nA note from Grok.\n\n'
            'Dragon here -I am the dragon.\n\n'
            'Alex here -I am Alex again.\n'
        ])
        self.assertEqual([m['spk'] for m in msgs], ['ALEX', 'VERTEX', 'PRISM', 'GROK', 'DRAGON', 'ALEX'])
        self.assertEqual(msgs[3]['embed_status'], 'EMBEDDED_PASTE')
        self.assertTrue(msgs[3]['source_marker'])
        self.assertTrue(any(line.startswith('Dragon here -') for line in msgs[4]['parts'][0]['lines']))
        for msg in msgs:
            if msg['spk'] != 'ALEX':
                self.assertNotEqual(msg['spk'], 'ALEX')
                self.assertIn(msg['embed_status'], ('LABELED_TURN', 'EMBEDDED_PASTE'))

    def test_alexandros_is_human_and_portuguese_prose_is_not_split(self):
        msgs = speakers([
            'Alexandros\n\n'
            'Podemos falar em Português? A Carla não é uma falante aqui. Copilot aparece só nesta frase.\n'
        ])
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]['spk'], 'ALEX')
        self.assertIn('Português', msgs[0]['parts'][0]['lines'][1])

    def test_newborn_paste_is_not_alex(self):
        msgs = speakers([
            "Alex\n\nI'm pasting them below.\n\nNewborn\n\nHello Alex. Welcome.\n"
        ], 'grok')
        self.assertEqual([m['spk'] for m in msgs], ['ALEX', 'NEWBORN'])
        self.assertEqual(msgs[1]['embed_status'], 'EMBEDDED_PASTE')
        self.assertNotIn('Hello Alex.', '\n'.join(msgs[0]['parts'][0]['lines']))


if __name__ == '__main__':
    unittest.main()

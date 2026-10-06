import json
import os
import unittest
from datetime import date
from unittest.mock import patch

import requests
import main


def paper(number, abstract=True, title='Catalysis study'):
    return {'id': f'https://openalex.org/W{number}', 'doi': f'https://doi.org/10.test/{number}',
            'display_name': title, 'publication_date': f'2026-10-{number:02d}',
            'abstract_inverted_index': {'New': [0], 'catalyst': [1]} if abstract else None}


class BotTests(unittest.TestCase):
    def test_abstract_word_order_and_repeated_words(self):
        self.assertEqual(main.reconstruct_abstract({'reaction': [1], 'The': [0, 2]}), 'The reaction The')
        self.assertIsNone(main.reconstruct_abstract(None))

    def test_selection_is_unique_recent_and_prefers_abstracts(self):
        works = [paper(5, False), paper(1), paper(4), paper(2), paper(4)]
        self.assertEqual([p['id'] for p in main.select_papers(works)],
                         ['https://openalex.org/W4', 'https://openalex.org/W2', 'https://openalex.org/W1'])
        self.assertEqual(len(main.select_papers([paper(1)])), 1)

    @patch('main.requests.get')
    def test_fetch_query_and_http_failure(self, get):
        get.return_value.json.return_value = {'results': [paper(1)]}
        self.assertEqual(len(main.fetch_papers(date(2026, 10, 7))), 1)
        params = get.call_args.kwargs['params']
        self.assertIn('from_publication_date:2026-10-04', params['filter'])
        self.assertNotIn('api_key', params)
        get.return_value.raise_for_status.side_effect = requests.HTTPError()
        with self.assertRaises(requests.HTTPError):
            main.fetch_papers(date(2026, 10, 7))

    @patch('main.requests.post')
    def test_explanation_uses_only_supplied_abstract_and_validates_json(self, post):
        data = dict(study='研究', novelty='新規性', usefulness='意義', limitations='未確認')
        post.return_value.json.return_value = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(data)}]}}]}
        self.assertEqual(main.explain_paper(paper(1), 'test-key', 'gemini-test-model'), data)
        payload = post.call_args.kwargs['json']
        source = json.loads(payload['contents'][0]['parts'][0]['text'])
        self.assertEqual(source['abstract'], 'New catalyst')
        self.assertEqual(post.call_args.args[0], 'https://generativelanguage.googleapis.com/v1beta/models/gemini-test-model:generateContent')
        self.assertEqual(post.call_args.kwargs['headers'], {'x-goog-api-key': 'test-key'})
        self.assertNotIn('test-key', post.call_args.args[0])
        self.assertEqual(payload['generationConfig']['responseSchema']['required'], list(data))
        post.return_value.json.return_value = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{}'}]}}]}
        with self.assertRaises(ValueError):
            main.explain_paper(paper(1), 'test-key', 'gemini-test-model')

    @patch('main.requests.post')
    def test_gemini_rejects_blocked_truncated_and_malformed_outputs(self, post):
        invalid = [
            {'promptFeedback': {'blockReason': 'SAFETY'}},
            {'candidates': []},
            {'candidates': [{'finishReason': 'SAFETY'}]},
            {'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': '{}'}]}}]},
            {'candidates': [{'finishReason': 'STOP', 'content': {'parts': []}}]},
            {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '[]'}]}}]},
            {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{broken'}]}}]},
            {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{"study": 3}'}]}}]},
        ]
        for result in invalid:
            with self.subTest(result=result):
                post.return_value.json.return_value = result
                with self.assertRaises(ValueError):
                    main.explain_paper(paper(1), 'test-key', 'gemini-test')

    @patch('main.requests.post')
    def test_gemini_ignores_thought_parts_and_combines_text(self, post):
        data = dict(study='研究', novelty='新規性', usefulness='意義', limitations='未確認')
        text = json.dumps(data)
        post.return_value.json.return_value = {'candidates': [{'finishReason': 'STOP', 'content': {
            'parts': [{'thought': True, 'text': 'not final JSON'},
                      {'text': text[:20]}, {'text': text[20:]}]}}]}
        self.assertEqual(main.explain_paper(paper(1), 'test-key', 'gemini-test'), data)

    @patch('main.requests.post')
    def test_gemini_http_failures_propagate(self, post):
        post.return_value.raise_for_status.side_effect = requests.HTTPError()
        with self.assertRaises(requests.HTTPError):
            main.explain_paper(paper(1), 'test-key', 'gemini-test')

    @patch('main.requests.post')
    def test_invalid_model_is_rejected_before_network_request(self, post):
        for model in ['https://example.com', 'models/gemini-2.5-flash', 'gemini-test?key=leak']:
            with self.subTest(model=model), self.assertRaises(ValueError):
                main.explain_paper(paper(1), 'test-key', model)
        post.assert_not_called()

    def test_discord_limits_and_mentions(self):
        papers = [paper(i, title='@everyone *' + '長' * 4000) for i in range(1, 4)]
        explanation = {k: '@everyone ' + '長' * 4000 for k in ['study', 'novelty', 'usefulness', 'limitations']}
        messages = main.build_messages(papers, date(2026, 10, 7), explanation, papers[0])
        self.assertEqual(len(messages), 2)
        self.assertTrue(all(len(m) <= 2000 for m in messages))
        self.assertTrue(all('@everyone' not in m for m in messages))
        with patch('main.requests.post') as post:
            main.send_messages('https://discord.invalid/test', messages)
            self.assertEqual(post.call_count, 2)
            self.assertEqual(post.call_args.kwargs['json']['allowed_mentions'], {'parse': []})
            post.return_value.raise_for_status.side_effect = requests.HTTPError()
            with self.assertRaises(requests.HTTPError):
                main.send_messages('https://discord.invalid/test', messages)

    @patch.dict(os.environ, {}, clear=True)
    @patch('main.fetch_papers', return_value=[])
    @patch('main.send_messages')
    @patch('sys.argv', ['main.py', '--dry-run'])
    def test_dry_run_never_posts(self, send, fetch):
        main.main()
        send.assert_not_called()

    @patch.dict(os.environ, {'DISCORD_WEBHOOK_URL': 'https://discord.invalid/test'}, clear=True)
    @patch('main.fetch_papers', return_value=[paper(1)])
    @patch('main.send_messages')
    @patch('sys.argv', ['main.py'])
    def test_missing_ai_key_is_reported_without_fake_explanation(self, send, fetch):
        main.main()
        self.assertIn('GEMINI_API_KEY', send.call_args.args[1][1])

    @patch.dict(os.environ, {'DISCORD_WEBHOOK_URL': 'https://discord.invalid/test', 'GEMINI_API_KEY': 'test-key'}, clear=True)
    @patch('main.fetch_papers', return_value=[paper(1)])
    @patch('main.explain_paper', side_effect=requests.HTTPError())
    @patch('main.send_messages')
    @patch('sys.argv', ['main.py'])
    def test_ai_failure_still_delivers_recommendations(self, send, explain, fetch):
        main.main()
        messages = send.call_args.args[1]
        self.assertIn('生成に失敗', messages[1])
        self.assertIn('Catalysis study', messages[0])

    @patch.dict(os.environ, {'DISCORD_WEBHOOK_URL': 'https://discord.invalid/test', 'GEMINI_API_KEY': 'test-key'}, clear=True)
    @patch('main.fetch_papers', return_value=[paper(3), paper(2), paper(1)])
    @patch('main.explain_paper', return_value=dict(study='研究', novelty='新規性', usefulness='意義', limitations='未確認'))
    @patch('main.send_messages')
    @patch('sys.argv', ['main.py'])
    def test_daily_flow_explains_exactly_one(self, send, explain, fetch):
        main.main()
        explain.assert_called_once()
        self.assertEqual(explain.call_args.args[0]['id'], 'https://openalex.org/W3')
        self.assertEqual(explain.call_args.args[2], 'gemini-2.5-flash')
        self.assertEqual(len(send.call_args.args[1]), 2)

    def test_empty_and_no_abstract_messages(self):
        self.assertIn('見つかりません', main.build_messages([], date(2026, 10, 7))[0])
        self.assertIsNone(main.explain_paper(paper(1, False), 'test-key', 'gemini-test-model'))


if __name__ == '__main__':
    unittest.main()

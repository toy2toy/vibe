import sys
from types import SimpleNamespace
from unittest import TestCase, mock

import main as cm


class ExtractTextTests(TestCase):
    def test_extract_text_string(self):
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Sunny day"))]
        )
        self.assertEqual(cm.extract_text(response), "Sunny day")

    def test_extract_text_list(self):
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=[
                            SimpleNamespace(type="text", text="Hello "),
                            SimpleNamespace(type="text", text="world"),
                        ]
                    )
                )
            ]
        )
        self.assertEqual(cm.extract_text(response), "Hello world")

    def test_extract_text_missing(self):
        self.assertEqual(cm.extract_text(None), "")


class GeocodeTests(TestCase):
    @mock.patch("main.get_with_retry")
    def test_geocode_success(self, mock_get):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {
            "results": [
                {
                    "name": "Dali",
                    "admin1": "Yunnan",
                    "country": "China",
                    "latitude": 25.6,
                    "longitude": 100.2,
                }
            ]
        }
        mock_get.return_value = mock_resp

        lat, lon, display = cm.geocode("Dali")
        self.assertEqual((lat, lon), (25.6, 100.2))
        self.assertEqual(display, "Dali, Yunnan, China")

    @mock.patch("main.get_with_retry")
    def test_geocode_no_results_exits(self, mock_get):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {"results": []}
        mock_get.return_value = mock_resp
        with self.assertRaises(SystemExit):
            cm.geocode("Nowhere")


class FetchWeatherTests(TestCase):
    @mock.patch("main.get_with_retry")
    def test_fetch_weather_returns_current_weather(self, mock_get):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {"current_weather": {"temperature": 20}}
        mock_get.return_value = mock_resp

        self.assertEqual(cm.fetch_weather(1.0, 2.0), {"temperature": 20})

    @mock.patch("main.get_with_retry")
    def test_fetch_weather_missing_current_weather_exits(self, mock_get):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp
        with self.assertRaises(SystemExit):
            cm.fetch_weather(1.0, 2.0)


class RunFlowTests(TestCase):
    @mock.patch("main.load_env")
    @mock.patch("main.create_chat_with_retry")
    @mock.patch("main.fetch_weather")
    @mock.patch("main.geocode")
    @mock.patch("main.OpenAI")
    def test_run_happy_path(self, mock_openai, mock_geocode, mock_fetch, mock_chat, mock_load_env):
        mock_geocode.return_value = (1.0, 2.0, "Test Place")
        mock_fetch.return_value = {"temperature": 21, "windspeed": 4}
        mock_chat.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Sunny and mild."))]
        )
        mock_openai.return_value = mock.Mock()

        self.assertEqual(cm.run("Test City"), "Sunny and mild.")
        mock_load_env.assert_called_once()
        mock_geocode.assert_called_once_with("Test City")
        mock_fetch.assert_called_once_with(1.0, 2.0)
        mock_chat.assert_called_once()

    @mock.patch("main.run")
    def test_main_prints_output(self, mock_run):
        mock_run.return_value = "Hello"
        with mock.patch.object(sys, "argv", ["main.py", "Test City"]), mock.patch(
            "builtins.print"
        ) as mock_print:
            cm.main()
        mock_run.assert_called_once_with("Test City")
        mock_print.assert_called_once_with("Hello")

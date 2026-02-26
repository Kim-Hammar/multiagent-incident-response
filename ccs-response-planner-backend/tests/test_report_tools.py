"""Unit tests for ReportAgent tool functions."""
import base64
from unittest.mock import MagicMock, patch

from ccs_response_planner_backend.agents.report_agent.tools import (
    generate_attack_image,
)


def _make_image_part(data: bytes = b"PNG_DATA",
                     mime: str = "image/png") -> MagicMock:
    """
    Create a mock Gemini inline_data part.

    :param data: raw image bytes
    :param mime: MIME type string
    :return: a MagicMock that looks like a Gemini Part
    """
    part = MagicMock()
    part.inline_data = MagicMock()
    part.inline_data.data = data
    part.inline_data.mime_type = mime
    return part


def _make_text_part(text: str = "done") -> MagicMock:
    """
    Create a mock Gemini text part (no image).

    :param text: text content
    :return: a MagicMock that looks like a text-only Part
    """
    part = MagicMock()
    part.inline_data = None
    part.text = text
    return part


@patch(
    "ccs_response_planner_backend.agents.report_agent"
    ".tools.genai",
)
def test_generate_attack_image_returns_image(
    mock_genai: MagicMock,
) -> None:
    """
    generate_attack_image returns a base64 data URL on success.
    """
    img_data = b"FAKE_PNG_BYTES"
    img_part = _make_image_part(img_data, "image/png")

    mock_response = MagicMock()
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [img_part]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = (
        mock_response
    )
    mock_genai.Client.return_value = mock_client

    result = generate_attack_image(prompt="test path")

    assert "image" in result
    expected_b64 = base64.b64encode(img_data).decode("ascii")
    assert result["image"] == (
        f"data:image/png;base64,{expected_b64}"
    )
    assert result["prompt"] == "test path"

    call_args = (
        mock_client.models.generate_content.call_args
    )
    assert call_args.kwargs["model"] == (
        "gemini-3.1-pro-image-preview"
    )


@patch(
    "ccs_response_planner_backend.agents.report_agent"
    ".tools.DatabaseFacade",
)
@patch(
    "ccs_response_planner_backend.agents.report_agent"
    ".tools.genai",
)
def test_generate_attack_image_with_incident_id(
    mock_genai: MagicMock,
    mock_db: MagicMock,
) -> None:
    """
    When incident_id is provided, the topology image is
    included in the request to the model.
    """
    topology_b64 = base64.b64encode(b"TOPO").decode("ascii")
    mock_db.get_example_incident.return_value = {
        "system_description_image": (
            f"data:image/png;base64,{topology_b64}"
        ),
    }

    img_data = b"RESULT_IMG"
    img_part = _make_image_part(img_data)
    mock_response = MagicMock()
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [img_part]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = (
        mock_response
    )
    mock_genai.Client.return_value = mock_client

    result = generate_attack_image(
        prompt="path desc", incident_id=1,
    )

    assert "image" in result
    mock_db.get_example_incident.assert_called_once_with(1)

    call_args = (
        mock_client.models.generate_content.call_args
    )
    contents = call_args.kwargs["contents"]
    assert len(contents) == 2
    assert "path desc" in contents[1]
    assert "attack path" in contents[1].lower()


@patch(
    "ccs_response_planner_backend.agents.report_agent"
    ".tools.genai",
)
def test_generate_attack_image_no_image_output(
    mock_genai: MagicMock,
) -> None:
    """
    When the model returns no image, an error dict is returned.
    """
    text_part = _make_text_part("no image generated")
    mock_response = MagicMock()
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content.parts = [text_part]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = (
        mock_response
    )
    mock_genai.Client.return_value = mock_client

    result = generate_attack_image(prompt="test")

    assert "error" in result
    assert result["prompt"] == "test"
    assert "no image" in result["error"].lower()


@patch(
    "ccs_response_planner_backend.agents.report_agent"
    ".tools.genai",
)
def test_generate_attack_image_api_error(
    mock_genai: MagicMock,
) -> None:
    """
    When the genai call raises, an error dict is returned.
    """
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = (
        RuntimeError("API quota exceeded")
    )
    mock_genai.Client.return_value = mock_client

    result = generate_attack_image(prompt="test")

    assert "error" in result
    assert "API quota exceeded" in result["error"]
    assert result["prompt"] == "test"

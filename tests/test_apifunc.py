import pytest
from src.apifunc.apifunc import (
    json_to_html,
    html_to_pdf,
    DynamicgRPCComponent,
    PipelineOrchestrator,
)

def test_json_to_html():
    sample_data = {"key1": "value1", "key2": "value2"}
    html_output = json_to_html(sample_data)
    assert "<td>key1</td>" in html_output
    assert "<td>value1</td>" in html_output

def test_html_to_pdf():
    html_content = "<html><body><h1>Test</h1></body></html>"
    pdf_output = html_to_pdf(html_content)
    assert isinstance(pdf_output, bytes)
    assert len(pdf_output) > 0

def test_dynamic_grpc_component():
    def mock_transform(data):
        return data.upper()

    component = DynamicgRPCComponent(mock_transform)
    input_data = "test"
    output_data = component.transform(input_data)
    assert output_data == "TEST"

def test_pipeline_orchestrator():
    def mock_transform_1(data):
        return data + " step1"

    def mock_transform_2(data):
        return data + " step2"

    component1 = DynamicgRPCComponent(mock_transform_1)
    component2 = DynamicgRPCComponent(mock_transform_2)

    pipeline = PipelineOrchestrator()
    pipeline.add_component(component1).add_component(component2)

    result = pipeline.execute_pipeline("start")
    assert result == "start step1 step2"
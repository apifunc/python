import os
import sys
sys.path.insert(0, os.path.abspath("./src"))
from apifunc.apifunc import example_usage
from apifunc.apifunc import ApiFuncConfig, ApiFuncFramework, DynamicgRPCComponent, PipelineOrchestrator
from apifunc.apifunc import json_to_html, html_to_pdf

if __name__ == "__main__":
    example_usage()
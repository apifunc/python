# [ apifunc: Modular Pipeline Framework with Dynamic graphs](https://github.com/tom-sapletta-com/apifunc)

+ [python.apifunc.com](http://python.apifunc.com)


RPC Services

## Overview

`apifunc` is a Python framework for building modular data processing pipelines. It allows you to define pipeline components as functions and dynamically generate gRPC services for them. This enables you to create flexible and scalable data processing workflows that can be easily integrated with other systems via gRPC.

## Key Features

*   **Modular Design:** Build pipelines from reusable components.
*   **Dynamic gRPC Generation:** Automatically generate gRPC service definitions and code from Python functions.
*   **Input Validation:** Each component can define its own input validation logic.
*   **Pipeline Orchestration:** Easily define and execute complex pipelines.
*   **Example Components:** Includes example components for JSON to HTML and HTML to PDF conversion.

## Installation

1.  **Clone the repository:**
```bash
git clone https://github.com/tom-sapletta-com/apifunc.git
```
2.  **Install the package:**
```bash
pip install .
```
## Usage

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

   
```bash
python cli.py run
``` 

```bash
python src/apifunc/cli.py run -o my_report.pdf
```

```bash
python src/apifunc/apifunc.py
```

```
pip install coverage
coverage run -m unittest discover -s tests
coverage report -m
python -m unittest discover -s tests
```


```
/home/linuxbrew/.linuxbrew/opt/python@3.11/bin/python -m venv venv
source venv/bin/activate
pip install grpcio grpcio-tools jinja2 weasyprint
python -m unittest tests.test_apifunc
```


To install the required dependencies for testing:
```
pip install jinja2 weasyprint grpcio grpcio-tools
```
    
This will generate `raport.pdf` file.

## Example

The `python/src/apifunc/apifunc.py` file includes a complete example that demonstrates:

*   Converting JSON data to HTML using Jinja2 templates.
*   Converting HTML to PDF using WeasyPrint.
*   Creating a pipeline with these two components.

## gRPC Service Generation

When you create a `DynamicgRPCComponent`, the framework automatically:

1.  Generates a `.proto` file defining a gRPC service with a `Transform` method.
2.  Compiles the `.proto` file into Python code.

The generated files are stored in the `generated_protos` directory.

## Dependencies

The project requires the following Python packages, as listed in `python/requirements.txt`:

*   `grpcio`
*   `grpcio-tools`
*   `protobuf`
*   `jinja2`
*   `weasyprint`

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.



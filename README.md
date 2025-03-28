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

    
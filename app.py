from flask import Flask, render_template, request
import subprocess
import os
import sys
import shutil

app = Flask(__name__)

# Finds the exact folder where app.py lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Prefer the local or parent virtual environment interpreter when available


def find_python_executable():
    candidates = [
        os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe"),
        os.path.join(BASE_DIR, os.pardir, ".venv", "Scripts", "python.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return sys.executable


def find_vpype_executable():
    candidates = [
        os.path.join(BASE_DIR, ".venv", "Scripts", "vpype.exe"),
        os.path.join(BASE_DIR, os.pardir, ".venv", "Scripts", "vpype.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return shutil.which("vpype")


VENV_PYTHON = find_python_executable()
VENV_VPYPE = find_vpype_executable()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return "No file selected"

    img_path = os.path.join(BASE_DIR, "input.png")
    bmp_path = os.path.join(BASE_DIR, "input.bmp")
    svg_path = os.path.join(BASE_DIR, "output.svg")
    gcode_path = os.path.join(BASE_DIR, "final.gcode")

    file.save(img_path)

    potrace_exe = os.path.join(BASE_DIR, "potrace.exe")
    if not os.path.exists(potrace_exe):
        return f"<h1>Error:</h1><pre>potrace.exe not found at {potrace_exe}</pre>"

    try:
        # 1. ImageMagick
        subprocess.run(
            [
                "magick",
                "convert",
                img_path,
                "-threshold",
                "50%",
                f"BMP3:{bmp_path}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # 2. Potrace
        subprocess.run(
            [potrace_exe, bmp_path, "-b", "svg", "-o", svg_path],
            capture_output=True,
            text=True,
            check=True,
        )

        # 3. Vpype
        if os.path.exists(gcode_path):
            os.remove(gcode_path)

        import vpype_cli.cli as vpype_cli_module
        vpype_cmd_args = [
            "read",
            svg_path,
            "pagesize",
            "8.5inx11in",
            "linesort",
            "gwrite",
            "-p",
            "gcode",
            gcode_path,
        ]
        result_code = vpype_cli_module.main(
            vpype_cmd_args, standalone_mode=False)

        if result_code not in (None, 0):
            return f"<h1>Vpype failed:</h1><pre>Exit code {result_code}</pre>"

        if os.path.exists(gcode_path):
            return "<h1>SUCCESS: final.gcode created!</h1><a href='/'>Back</a>"
        return "<h1>G-Code failed: File not created</h1>"

    except subprocess.CalledProcessError as e:
        stderr = e.stderr or e.stdout or str(e)
        return f"<h1>Command failed:</h1><pre>{stderr}</pre>"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    #this is for github purposes said_innovates

#!/usr/bin/env python3

import argparse
import os
import signal
import socket
import subprocess
import sys
import time

TIMEOUT_SECONDS = 30
BUFFER_SIZE = 1024


def terminate_process(process: subprocess.Popen) -> None:
    """Terminate the process and its children, cross-platform."""

    if process.poll() is not None:
        return

    print("Stopping application...")

    try:
        if os.name == "nt":  # Windows
            subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(process.pid),
                    "/T",
                    "/F",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        else:  # POSIX
            try:
                os.killpg(process.pid, signal.SIGTERM)

                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)

            except ProcessLookupError:
                pass

    finally:  # Make absolutely sure the parent process is reaped.
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
                process.wait()
            except Exception:
                pass

    print("Stopped application (and all its children processes) :)")


def print_output(stdout: str, stderr: str) -> None:
    """Print captured application stdout/stderr."""

    print()
    print("========== APPLICATION STDOUT ==========")

    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")

    print()
    print("========== APPLICATION STDERR ==========")

    if stderr:
        print(stderr, end="" if stderr.endswith("\n") else "\n")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start an executable and wait for it to report READY via TCP.")

    parser.add_argument(
        "executable",
        help="Path to the executable to test",
    )

    args = parser.parse_args()

    executable_path = os.path.abspath(args.executable)

    if not os.path.isfile(executable_path):
        print(f"ERROR: Executable does not exist: {executable_path}", file=sys.stderr)
        return 1

    # Create a TCP listener on localhost using an automatically assigned port.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Allows the socket to be reused quickly after the script exits.
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    # Get the dynamically assigned port.
    port = listener.getsockname()[1]

    process = None

    try:
        # Start the executable.
        #
        # On POSIX, start a new process group so we can terminate
        # the executable and its children together.
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            creationflags = 0

        process = subprocess.Popen(
            [
                executable_path,
                "--ready-port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            start_new_session=(os.name != "nt"),
        )

        print(f"Started file {executable_path} process {process.pid}")
        print("Waiting for READY...")

        start_time = time.monotonic()

        # Use a short socket timeout so that we can periodically
        # check whether the process has died or the timeout expired.
        listener.settimeout(0.1)

        while True:

            # ---------------------------------------------------------
            # 1. Did the application connect and send READY?
            # ---------------------------------------------------------
            try:
                client, _address = listener.accept()

            except TimeoutError:
                client = None

            if client is not None:
                try:
                    client.settimeout(2)

                    data = client.recv(BUFFER_SIZE)

                    message = data.decode("utf-8").strip()

                    if message == "READY":
                        print("Application initialized successfully")
                        return 0

                    raise RuntimeError(f"Unexpected readiness message: '{message}'")

                finally:
                    client.close()

            # ---------------------------------------------------------
            # 2. Did the application die?
            # ---------------------------------------------------------
            exit_code = process.poll()

            if exit_code is not None:
                stdout, stderr = process.communicate()

                print_output(stdout, stderr)

                raise RuntimeError(f"Application exited before becoming ready. Exit code: {exit_code}")

            # ---------------------------------------------------------
            # 3. Did we exceed the timeout?
            # ---------------------------------------------------------
            elapsed = time.monotonic() - start_time

            if elapsed >= TIMEOUT_SECONDS:
                raise TimeoutError(f"Application did not become ready within {TIMEOUT_SECONDS} seconds")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    finally:
        listener.close()

        # Make sure the application doesn't remain running.
        if process is not None and process.poll() is None:
            terminate_process(process)

        # If the process has already exited, still collect its output
        # so that the pipes don't remain open.
        if process is not None and process.poll() is not None:
            try:
                process.communicate(timeout=1)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())

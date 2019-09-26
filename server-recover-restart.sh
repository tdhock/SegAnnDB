#!/bin/bash
set -o errexit
bash server-stop.sh
bash server-start.sh

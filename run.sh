#!/bin/bash

set -e

export FLASK_ENV="development"
export FLASK_APP="limud"

cd "$(dirname "${BASH_SOURCE[0]}")"
flask run
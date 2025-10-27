#!/bin/bash

set -e

path_to_run_from=${1:-/opt/fm_auth_service}
path_alembic=${2:-/opt/venvs/fm_auth_service/bin}
path_alembic_ini=${3:-/opt/venvs/fm_auth_service/lib/python3.7/site-packages}


cd "$path_to_run_from"

"$path_alembic"/alembic \
  -c "$path_alembic_ini"/alembic.ini \
  upgrade head

cd -

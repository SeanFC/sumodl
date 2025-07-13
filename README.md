# Sumo Download

Maintain a local repository of [Grand Sumo Highlights](https://www3.nhk.or.jp/nhkworld/en/tv/sumo/).
Includes features such as:
* auto download from NHK when new videos are available
* storing files to be compatible with [Jellyfin](https://jellyfin.org/)

## Running
Locally with 
```
uv run python -m sumodl
```
or through docker compose.

## Config
Done throught `.env` file. 
Available settings are:
* `MEDIA_DIRECTORY` - Where local media files are held

## Deploy
With [ansible](https://docs.ansible.com/), deploy to a running docker compose instance with

```
ansible-playbook deploy.yaml -i inventory.yaml
```
where inventory has hosts under `myhosts` with the vars the same as `.env`.

## Development 
Check and fix code with 
```
uv run ruff format
uv run pyright
```

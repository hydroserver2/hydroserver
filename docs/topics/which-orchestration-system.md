# Which Orchestration System Should You Use

HydroServer supports two orchestration systems for scheduled ETL: the Streaming Data Loader (SDL) desktop app and the Django Celery orchestration system that runs alongside your HydroServer instance. This page helps you choose between them.

## Quick guidance

Choose **Streaming Data Loader (SDL)** if you want:

- A simple, stand-alone desktop app
- Minimal infrastructure and ops overhead
- Local file or small API sources
- A quick way to get started for a single team or workstation

Choose **Django Celery** if you want:

- A server-side, always-on scheduler
- Centralized logs and monitoring
- Multiple users and many data connections
- A production deployment that should run without a desktop app

## Compare at a glance

| Decision factor      | Streaming Data Loader (SDL)            | Django Celery                          |
| -------------------- | -------------------------------------- | -------------------------------------- |
| Runs on              | A desktop or workstation               | Your HydroServer server                |
| Best for             | Small deployments, pilots, single team | Production, multi-team, high volume    |
| Ops overhead         | Low                                    | Medium                                 |
| Availability         | Depends on the desktop being on        | 24/7 with server uptime                |
| Scaling              | Limited to one machine                 | Scales with server resources           |
| Typical data sources | Local files, lightweight APIs          | Network-accessible APIs, hosted stores |
| Admin experience     | Desktop UI                             | Managed from HydroServer               |

## When SDL is the right fit

SDL is ideal if you want a lightweight scheduler without additional infrastructure. It shines when data is pulled from local files, you have a small number of data connections, or you want to keep the orchestration layer off the server. It's also a good fit for pilots, training, or field deployments where a desktop app is acceptable.

## When Django Celery is the right fit

Django Celery is the right choice when you need an always-on orchestration system that lives with HydroServer. If your deployment supports multiple users, has many data connections, or requires centralized scheduling and monitoring, Celery is the better long-term option. It also fits well when data sources are network-accessible and your HydroServer instance is already running in a server environment.

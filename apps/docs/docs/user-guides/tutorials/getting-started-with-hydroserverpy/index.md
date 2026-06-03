# Getting Started with hydroserverpy

`hydroserverpy` is HydroServer's official Python client library. It lets you do everything you can do in the web interface — creating sites, loading data, setting up automated ingestion — but from a Python script or notebook, which makes it easy to automate, repeat, and share your workflows.

In this tutorial series, you'll use `hydroserverpy` to build a complete end-to-end monitoring workflow for a stream gauge station. Here's what we'll cover across the five parts:

1. **Setting Up Your Site and Datastreams** — Connect to HydroServer and programmatically create your monitoring site, linked metadata, and datastreams.
2. **Loading and Visualizing Observations** — Load a set of historical stage observations into your datastream and plot them.
3. **Automating Data Ingestion** — Set up a data connection and ETL task to automatically pull new stage readings from a web API on a schedule.
4. **Creating Data Products** — Define a rating curve to convert stage measurements into discharge, and set up a data product task to compute and store discharge values automatically.
5. **Setting Up Monitoring** — Configure a monitoring task that checks your datastreams on a schedule and sends email alerts when values fall outside acceptable bounds.

Each part builds directly on the last, so work through them in order. By the end, you'll have a fully automated monitoring pipeline running in HydroServer — set up entirely through Python.

## Before You Begin

You'll need a HydroServer account. If you don't have one, you can create a free account on our public playground instance at [`https://playground.hydroserver.org`](https://playground.hydroserver.org).

### Python environment

This tutorial requires **Python 3.9 or higher** and uses **hydroserverpy 1.10.x**. We recommend installing into an isolated environment so it doesn't interfere with other projects on your machine. If you're using `venv`:

```bash
python -m venv hydroserver-env
source hydroserver-env/bin/activate  # On Windows: hydroserver-env\Scripts\activate
```

Or if you prefer `conda`:

```bash
conda create -n hydroserver-env python=3.11
conda activate hydroserver-env
```

Once your environment is active, install `hydroserverpy`:

```bash
pip install "hydroserverpy>=1.10,<1.11"
```

That's it — let's get started!

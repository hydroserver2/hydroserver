import random
from uuid import UUID
from django.core.management.base import CommandError
from domains.sta.models import Observation, Datastream


def generate_test_timeseries(datastream_id: UUID):
    """Populates a datastream with test timeseries domains."""

    try:
        datastream = Datastream.objects.get(pk=datastream_id)
    except Datastream.DoesNotExist:
        raise CommandError(f"Datastream {datastream_id} does not exist.")

    if not datastream.phenomenon_begin_time:
        raise CommandError("Datastream must have a phenomenon_begin_time.")

    if (
        not datastream.phenomenon_end_time
        or datastream.phenomenon_begin_time > datastream.phenomenon_end_time
    ):
        raise CommandError(
            "Datastream phenomenon_end_time must be after phenomenon_start_time."
        )

    if not datastream.value_count or datastream.value_count < 1:
        raise CommandError("Datastream value_count must be positive.")

    if datastream.value_count > 1000000:
        raise CommandError("Datastream value_count must be less than 1,000,000.")

    if Observation.objects.filter(datastream_id=datastream.id).exists():
        raise CommandError("Datastream already has observations loaded.")

    observations = []
    time_interval = (
        datastream.phenomenon_end_time - datastream.phenomenon_begin_time
    ) / datastream.value_count

    for i in range(datastream.value_count):
        phenomenon_time = datastream.phenomenon_begin_time + i * time_interval
        result = round(random.gauss(mu=10, sigma=1), 2)

        observations.append(
            Observation(
                datastream=datastream, phenomenon_time=phenomenon_time, result=result
            )
        )

        if len(observations) >= 100000:
            Observation.objects.bulk_copy(observations, batch_size=100000)
            observations.clear()

    if observations:
        Observation.objects.bulk_copy(observations)

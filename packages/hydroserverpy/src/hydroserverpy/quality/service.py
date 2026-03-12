import pandas as pd
import numpy as np
from uuid import UUID
from typing import Union, Optional, List, Tuple, Dict
from enum import Enum

# Tools
# [x] Interpolate
# [x] Set a value to a constant
# [x] Change value by applying arithmetic (+, -, *, /)
# [x] Shift
# [x] Drift correction (linear)
# [x] Delete values
# [x] Fill values

# Automation
# [x] Gap filling


class TimeUnit(Enum):
    """Enumeration for time units."""

    SECOND = "s"
    MINUTE = "m"
    HOUR = "h"
    DAY = "D"
    WEEK = "W"
    MONTH = "M"
    YEAR = "Y"


class FilterOperation(Enum):
    """Enumeration for filter operations."""

    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    E = "E"


class Operator(Enum):
    """Enumeration for mathematical operations."""

    MULT = "MULT"
    DIV = "DIV"
    ADD = "ADD"
    SUB = "SUB"
    ASSIGN = "ASSIGN"


class HydroServerQualityControl:
    """
    Quality control operations for HydroServer observations.

    :param datastream_id: The ID of the datastream.
    :type datastream_id: Union[UUID, str]
    :param observations: DataFrame containing 'timestamp' and 'value' columns.
    :type observations: pd.DataFrame
    """

    datastream_id: Union[UUID, str]

    def __init__(
        self, datastream_id: Union[UUID, str], observations: pd.DataFrame
    ) -> None:

        assert (
            "timestamp" in observations.columns
        ), "Observations must have a 'timestamp' column"
        assert pd.api.types.is_datetime64_any_dtype(
            observations["timestamp"]
        ), "Observations 'timestamp' column must be of datetime type"

        assert (
            "value" in observations.columns
        ), "Observations must have a 'value' column"
        assert pd.api.types.is_float_dtype(
            observations["value"]
        ), "Observations 'value' column must be of float type"

        self.datastream_id = str(datastream_id)
        self._df = observations
        self._filtered_observations = None

    @property
    def observations(self) -> pd.DataFrame:
        """
        Returns the observations DataFrame, filtered if a filter has been applied.

        :return: Observations DataFrame.
        :rtype: pd.DataFrame
        """

        if self._filtered_observations is None:
            return self._df

        return self._filtered_observations

    ###################
    # Filters
    ###################

    @staticmethod
    def _has_filter(
        data_filter: Dict[str, Union[float, int]], key: FilterOperation
    ) -> bool:
        """
        Checks if a given filter operation exists in the filter dictionary.

        :param data_filter: Dictionary containing the filters.
        :type data_filter: Dict[str, Union[float, int]]
        :param key: Filter operation to check for.
        :type key: FilterOperation
        :return: True if the filter operation exists, False otherwise.
        :rtype: bool
        """

        return key.value in data_filter and (
            isinstance(data_filter[key.value], float)
            or isinstance(data_filter[key.value], int)
        )

    def filter(self, data_filter: Dict[str, Union[float, int]]) -> None:
        """
        Executes the applied filters and returns the resulting DataFrame.

        :param data_filter: Dictionary containing filter operations and their values.
        :type data_filter: Dict[str, Union[float, int]]
        """

        query = []

        if self._has_filter(data_filter, FilterOperation.LT):
            query.append(f"`value` < {data_filter[FilterOperation.LT.value]}")

        if self._has_filter(data_filter, FilterOperation.LTE):
            query.append(f"`value` <= {data_filter[FilterOperation.LTE.value]}")

        if self._has_filter(data_filter, FilterOperation.GT):
            query.append(f"`value` > {data_filter[FilterOperation.GT.value]}")

        if self._has_filter(data_filter, FilterOperation.GTE):
            query.append(f"`value` >= {data_filter[FilterOperation.GTE.value]}")

        if self._has_filter(data_filter, FilterOperation.E):
            query.append(f"`value` == {data_filter[FilterOperation.E.value]}")

        if len(query):
            self._filtered_observations = self._df.query(" | ".join(query))
        else:
            self._filtered_observations = None

    ###################
    # Gap Analysis
    ###################

    def find_gaps(self, time_value: int, time_unit: str) -> pd.DataFrame:
        """
        Identifies gaps in the observations based on the specified time value and unit.

        :param time_value: The time value for detecting gaps.
        :type time_value: int
        :param time_unit: The unit of time (e.g., 's', 'm', 'h').
        :type time_unit: str
        :return: DataFrame containing the observations with gaps.
        :rtype: pd.DataFrame
        """

        return self.observations[
            self._df["timestamp"].diff() > np.timedelta64(time_value, time_unit)
        ]

    def fill_gap(
        self, gap: Tuple[int, str], fill: Tuple[int, str], interpolate_values: bool
    ) -> pd.DataFrame:
        """
        Fills identified gaps in the observations with placeholder values and optionally interpolates the values.

        :param gap: Tuple containing the time value and unit for identifying gaps.
        :type gap: Tuple[int, str]
        :param fill: Tuple containing the time value and unit for filling gaps.
        :type fill: Tuple[int, str]
        :param interpolate_values: Whether to interpolate values for the filled gaps.
        :type interpolate_values: bool
        :return: DataFrame of points that filled the gaps.
        :rtype: pd.DataFrame
        """

        gaps_df = self.find_gaps(gap[0], gap[1])
        time_gap = np.timedelta64(fill[0], fill[1])
        points = []
        index = []
        added_index = []

        for gap_row in gaps_df.iterrows():
            gap_end_index = gap_row[0]
            gap_start_index = gap_end_index - 1

            gap_start_date = self._df.iloc[gap_start_index]["timestamp"]
            gap_end_date = self._df.iloc[gap_end_index]["timestamp"]

            start = gap_start_date + time_gap
            end = gap_end_date

            # Annotate the points that will fill this gap
            while start < end:
                points.append([start, -9999])
                index.append(gap_start_index)
                start = start + time_gap

                if interpolate_values:
                    # Keep an index of the position where the points will end up
                    added_index.append(gap_start_index + len(added_index) + 1)

        self.add_points(points, index)

        if interpolate_values:
            self.interpolate(added_index)

        # Return the list of points that filled the gaps
        return pd.DataFrame(points, columns=["timestamp", "value"])

    ######################################
    # Data point operations
    ######################################

    def add_points(
        self, points: List[List[Union[str, float]]], index: Optional[List[int]] = None
    ) -> None:
        """
        Adds new points to the observations, optionally at specified indices.

        :param points: List of points to be added.
        :type points: List[List[Union[str, float]]]
        :param index: Optional list of indices at which to insert the points.
        :type index: Optional[List[int]]
        """

        # If an index list was provided, insert the points to the DataFrame at the corresponding index.
        # We do this by creating a dictionary of slices where the key is the index to insert at, and the value is an
        # array of points to insert at that index
        # We iterate through the dictionary keys in reverse order, so that we can insert without altering the position
        # of elements before
        if index is not None:
            # This is the most efficient way to insert into a DataFrame for a large dataset.

            # create a dictionary of points to insert at each index
            slices = {}
            for idx, value in enumerate(index):
                if value not in slices:
                    slices[value] = []

                slices[value].append(points[idx])

            for s in sorted(slices.items(), reverse=True):
                # Split DataFrame and insert new row.
                idx = s[0] + 1
                val = s[1]
                df1 = self._df.iloc[:idx, :]
                df2 = self._df.iloc[idx:, :]

                points_df = pd.DataFrame(val, columns=["timestamp", "value"])
                self._df = pd.concat([df1, points_df, df2]).reset_index(drop=True)

        else:
            # This way of inserting is not as efficient, but performance should be good enough given that the existing
            # data in the DataFrame is pre-sorted.

            # Create a new dataframe with the points
            points_df = pd.DataFrame(points, columns=["timestamp", "value"])

            # Concatenate both dataframes. New rows will be at the end.
            self._df = pd.concat([self._df, points_df])

            # Sort and reset index
            self._df = self._df.sort_values("timestamp")
            self._df.reset_index(drop=True, inplace=True)

    def change_values(
        self, index_list: List[int], operator: str, value: Union[int, float]
    ) -> None:
        """
        Changes the values of observations based on the specified operator and value.

        :param index_list: List of indices for which values will be changed.
        :type index_list: List[int]
        :param operator: The operation to perform ('MULT', 'DIV', 'ADD', 'SUB', 'ASSIGN').
        :type operator: str
        :param value: The value to use in the operation.
        :type value: Union[int, float]
        """

        def operation(x):
            if operator == Operator.MULT.value:
                return x * value
            elif operator == Operator.DIV.value:
                if value == 0:
                    print("Error: cannot divide by 0")
                    return x
                return x / value
            elif operator == Operator.ADD.value:
                return x + value
            elif operator == Operator.SUB.value:
                return x - value
            elif operator == Operator.ASSIGN.value:
                return value
            else:
                return x

        self._df.loc[index_list, "value"] = self._df.loc[index_list, "value"].apply(
            operation
        )

    def delete_points(self, index_list: List[int]) -> None:
        """
        Deletes points from the observations at the specified indices.

        :param index_list: List of indices for which points will be deleted.
        :type index_list: List[int]
        """

        self._df.drop(index=index_list, inplace=True)
        self._df.reset_index(drop=True, inplace=True)

    def shift_points(
        self, index_list: List[int], time_value: int, time_unit: str
    ) -> None:
        """
        Shifts the timestamps of the observations at the specified indices by a given time value and unit.

        :param index_list: List of indices where timestamps will be shifted.
        :type index_list: List[int]
        :param time_value: The amount of time to shift the timestamps.
        :type time_value: int
        :param time_unit: The unit of time (e.g., 's' for seconds, 'm' for minutes).
        :type time_unit: str
        """

        shift_value = np.timedelta64(time_value, time_unit)
        condition = self._df.index.isin(index_list)

        # Apply the shift
        self._df.loc[condition, "timestamp"] = (
            self._df.loc[condition, "timestamp"] + shift_value
        )
        self._df = self._df.sort_values("timestamp")
        self._df.reset_index(drop=True, inplace=True)

    def interpolate(self, index_list: List[int]) -> None:
        """
        Interpolates the values of observations at the specified indices using linear interpolation.

        :param index_list: List of indices where values will be interpolated.
        :type index_list: list[int]
        """

        condition = self._df.index.isin(index_list)
        self._df["value"].mask(condition, inplace=True)
        self._df["value"].interpolate(method="linear", inplace=True)

    def drift_correction(self, start: int, end: int, gap_width: float) -> pd.DataFrame:
        """
        Applies drift correction to the values of observations within the specified index range.

        :param start: Start index of the range to apply drift correction.
        :type start: int
        :param end: End index of the range to apply drift correction.
        :type end: int
        :param gap_width: The width of the drift gap to correct.
        :type gap_width: float
        :return: DataFrame after applying drift correction.
        :rtype: pd.DataFrame
        """

        # validate range
        if start >= end:
            print("Start and end index cannot overlap")
            return self._df
        elif end > len(self._df) - 1:
            print("End index out of range")
            return self._df
        elif start < 0:
            print("Start index must be greater than or equal to 0")
            return self._df

        points = self._df.iloc[start : end + 1]
        start_date = points.iloc[0]["timestamp"]
        end_date = points.iloc[-1]["timestamp"]

        x_l = (end_date - start_date).total_seconds()
        ndv = -9999
        # y_n = y_0 + G(x_i / x_l)

        def f(row):
            if row["value"] != ndv:
                return row["value"] + (
                    gap_width * ((row["timestamp"] - start_date).total_seconds() / x_l)
                )
            else:
                return row["value"]

        self._df.loc[points.index, "value"] = points.apply(f, axis=1)

        return self._df

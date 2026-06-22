import pandas as pd
import numpy as np
from datetime import datetime
from enum import Enum

# Tools
# [x] Interpolate
# [x] Set a value to a constant
# [x] Change value by applying arithmetic (+, -, *, /)
# [x] Shift
# [x] Drift correction (linear)
# [x] Delete values
# [x] Fill values
# [x] Filter by value threshold
# [x] Persistence
# [x] Rate of change
# [x] Find Gaps

# Automation
# [x] Gap filling


DATETIME_COL_INDEX = 0
VALUE_COL_INDEX = 1
QUALIFIER_COL_INDEX = 2

class TimeUnit(Enum):
  SECOND = 's'
  MINUTE = 'm'
  HOUR = 'h'
  DAY = 'D'
  WEEK = 'W'
  MONTH = 'M'
  YEAR = 'Y'


class FilterOperation(Enum):
  # Value filters
  LT = 'LT'
  LTE = 'LTE'
  GT = 'GT'
  GTE = 'GTE'
  E = 'E'

  # Datetime range filters
  START = 'START'
  END = 'END'

class RateOfChangeOperation(Enum):
  LT = 'LT'
  LTE = 'LTE'
  GT = 'GT'
  GTE = 'GTE'
  E = 'E'

class Operator(Enum):
  ADD = 'ADD'
  SUB = 'SUB'
  MULT = 'MULT'
  DIV = 'DIV'
  ASSIGN = 'ASSIGN'

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class EditService():
  def __init__(self, data) -> None:
    self.data = data
    self._populate_series()

  def _populate_series(self) -> None:
    rows = self.data["dataArray"]
    cols = self.data["components"]

    for i, r in enumerate(rows):
      # parse datetime
      rows[i][DATETIME_COL_INDEX] = datetime.strptime(
        r[DATETIME_COL_INDEX], ISO_FORMAT)
      
      # extract qualifier codes
      rows[i][QUALIFIER_COL_INDEX] = [q['code'] for q in r[QUALIFIER_COL_INDEX]['resultQualifiers']]
    self._df = pd.DataFrame(rows, columns=cols)

  def get_dataframe(self):
    return self._df

  def get_date_col(self):
    return self.data["components"][DATETIME_COL_INDEX]

  def get_value_col(self):
    return self.data["components"][VALUE_COL_INDEX]
  
  def get_qualifier_col(self):
    return self.data["components"][QUALIFIER_COL_INDEX]

  ###################
  # Filters
  # filter operations return a new DataFrame object and do not modify the current DataFrame.
  ###################

  def _has_filter(self, filter: dict[FilterOperation, float], key: FilterOperation) -> bool:
    return key.value in filter and (isinstance(filter[key.value], float) or isinstance(filter[key.value], int))

  def filter(self, filter: dict[FilterOperation, float]) -> None:
    """
    Executes the applied filters and returns the resulting DataFrame

    :return: Pandas DataFrame object
    """

    query = []

    # VALUE FILTERS
    if self._has_filter(filter, FilterOperation.LT):
      query.append(
        f'`{self.get_value_col()}` < {filter[FilterOperation.LT.value]}')

    if self._has_filter(filter, FilterOperation.LTE):
      query.append(
        f'`{self.get_value_col()}` <= {filter[FilterOperation.LTE.value]}')

    if self._has_filter(filter, FilterOperation.GT):
      query.append(
        f'`{self.get_value_col()}` > {filter[FilterOperation.GT.value]}')

    if self._has_filter(filter, FilterOperation.GTE):
      query.append(
        f'`{self.get_value_col()}` >= {filter[FilterOperation.GTE.value]}')

    if self._has_filter(filter, FilterOperation.E):
      query.append(
        f'`{self.get_value_col()}` == {filter[FilterOperation.E.value]}')
      
    # DATETIME FILTERS
    if self._has_filter(filter, FilterOperation.START):
      query.append(
        f'`{self.get_date_col()}` >= {filter[FilterOperation.START.value]}')
      
    if self._has_filter(filter, FilterOperation.END):
      query.append(
        f'`{self.get_date_col()}` <= {filter[FilterOperation.END.value]}')

    if len(query):
      return self._df.query(" | ".join(query))
    else:
      return None

  def find_gaps(self, time_value, time_unit: str, range = None):
    """
    Find gaps in the DataFrame.

    :return: Pandas DataFrame object
    """

    df = None
    if range:
      df = self.get_dataframe().iloc[range[0]:range[1] + 1]
    else:
      df = self.get_dataframe()

    # DataFrame.diff calculates the difference of datetime compared with the element in previous row.
    return df.loc[self._df[self.get_date_col()].diff() > np.timedelta64(time_value, time_unit)]
  
  def rate_of_change(self, comparator: RateOfChangeOperation, value: float, range = None):
    """
    Returns a DataFrame filtered by provided rate of change.

    :return: Pandas DataFrame object
    """
        
    df = None
    if range:
      df = self.get_dataframe().iloc[range[0]:range[1] + 1]
    else:
      df = self.get_dataframe()

    # Calculate percentage change
    # Round to the same number of decimals in `value` so we can compare for equality
    decimals = 0
    number_string = str(value)

    if "." in number_string:
        decimals = len(number_string.split(".")[1])
    df_pct_change = df['value'].pct_change().round(decimals)

    if comparator == RateOfChangeOperation.LT:
      return df[df_pct_change < value]
    elif comparator == RateOfChangeOperation.LTE:
        return df[df_pct_change <= value]
    elif comparator == RateOfChangeOperation.GT:
        return df[df_pct_change > value]
    elif comparator == RateOfChangeOperation.GTE:
        return df[df_pct_change >= value]
    elif comparator == RateOfChangeOperation.E:
        return df[df_pct_change == value]
    
    # default
    return df
  
  def persistence(self, times, range = None):
    """
    Returns a DataFrame filtered where values remain the same for `times` in a row.

    :return: Pandas DataFrame object
    """

    df = None
    if range:
      df = self.get_dataframe().iloc[range[0]:range[1] + 1]
    else:
      df = self.get_dataframe()

    # Create a boolean mask for rows part of a consecutive group of at least x 
    def mark_consecutive_groups(df, x): 
      df['group'] = (df['value'] != df['value'].shift()).cumsum() 
      group_counts = df.groupby('group')['value'].transform('count') 
      df['consecutive'] = (group_counts >= x) 
      return df

    # Apply the function and filter the DataFrame
    df_marked = mark_consecutive_groups(df, times) 
    return df[df_marked['consecutive']].drop(columns=['group', 'consecutive'])


  ######################################
  # Data point operations
  # These operations modify the DataFrame in place.
  ######################################
  def fill_gaps(self, gap, fill, interpolate_values, range = None):
    """
    :return Pandas DataFrame:
    """
    gaps_df = self.find_gaps(gap[0], gap[1], range)
    timegap = np.timedelta64(fill[0], fill[1])
    points = []
    index = []
    added_index = []

    for gap_row in gaps_df.iterrows():
      gap_end_index = gap_row[0]
      gap_start_index = gap_row[0] - 1

      if range and gap_start_index < range[0]:
        continue

      gap_start_date = self._df.iloc[gap_start_index][self.get_date_col()]
      gap_end_date = self._df.iloc[gap_end_index][self.get_date_col()]

      start = gap_start_date + timegap

      # Annotate the points that will fill this gap
      while start < gap_end_date:
        points.append([start, -9999, []])
        index.append(gap_start_index)
        start = start + timegap

        if (interpolate_values):
          # Keep an index of the position where the points will end up
          added_index.append(gap_start_index + len(added_index) + 1)

    self.add_points(points, index)

    if (interpolate_values):
      self.interpolate(added_index)

    # Return the list of points that filled the gaps
    return pd.DataFrame(
      points, columns=[self.get_date_col(), self.get_value_col(), self.get_qualifier_col()])

  def add_points(self, points, index=None):
    """
    Inserts data points in the DataFrame. The index will be reset.

    :return Pandas DataFrame:
    """

    # If an index list was provided, insert the points to the DataFrame at the corresponding index.
    # We do this by creating a dictionary of slices where the key is the index to insert at, and the value is an array of points to insert at that index
    # We iterate through the dictionary keys in reverse order, so that we can insert without altering the position of elements before
    if index is not None:
      # This is the most efficient way to insert into a DataFrame for a large dataset.

      # create a dictionary of points to insert at each index
      slices = {}
      for idx, value in enumerate(index):
        if not value in slices:
          slices[value] = []

        slices[value].append(points[idx])

      for s in sorted(slices.items(), reverse=True):
        # Split DataFrame and insert new row.
        idx = s[0] + 1
        val = s[1]
        df1 = self._df.iloc[:idx, :]
        df2 = self._df.iloc[idx:, :]

        points_df = pd.DataFrame(
          val, columns=[self.get_date_col(), self.get_value_col(), self.get_qualifier_col()])
        self._df = pd.concat([df1, points_df, df2]).reset_index(drop=True)

    else:
      # This way of inserting is not as efficient, but performance should be good enough given that the existing data in the DataFrame is pre-sorted.

      # Create a new dataframe with the points
      points_df = pd.DataFrame(
        points, columns=[self.get_date_col(), self.get_value_col(), self.get_qualifier_col()])

      # Concatenate both dataframes. New rows will be at the end.
      self._df = pd.concat([self._df, points_df])

      # Sort and reset index
      self._df = self._df.sort_values(self.get_date_col())
      self._df.reset_index(drop=True, inplace=True)

  def change_values(self, index_list, operator: str, value):
    """
    Perform an operation on the DataFrame value column.
    """
        
    def operation(x):
      if operator == Operator.MULT.value:
        return x * value
      elif operator == Operator.DIV.value:
        if value == 0:
          raise Exception("Cannot divide by 0")
        return x / value
      elif operator == Operator.ADD.value:
        return x + value
      elif operator == Operator.SUB.value:
        return x - value
      elif operator == Operator.ASSIGN.value:
        return value
      else:
        return x

    self._df.loc[index_list, self.get_value_col(
    )] = self._df.loc[index_list, self.get_value_col()].apply(operation)

  def delete_points(self, index_list):
    """
    Deletes rows in the DataFrame.
    """
        
    self._df.drop(index=index_list, inplace=True)
    self._df.reset_index(drop=True, inplace=True)

  def shift_points(self, index_list, time_value, time_unit):
    """
    Shift the date column in the DataFrame.
    """
        
    shift_value = np.timedelta64(time_value, time_unit)
    condition = self._df.index.isin(index_list)

    # Apply the shift
    self._df.loc[condition, self.get_date_col()] = self._df.loc[condition,
                                                                self.get_date_col()] + shift_value

    self._df = self._df.sort_values(self.get_date_col())
    self._df.reset_index(drop=True, inplace=True)

  def interpolate(self, index_list):
    """
    Interpolates the value column in DataFrame. Uses linear interpolation.
    """

    condition = self._df.index.isin(index_list)
    self._df[self.get_value_col()].mask(condition, inplace=True)
    self._df[self.get_value_col()].interpolate(method="linear", inplace=True)

  def drift_correction(self, start, end, gap_width):
    """
    Performs drift correction.

    :return: Pandas DataFrame object
    """
        
    # validate range
    if start >= end:
      raise Exception("Start and end index cannot overlap")
    elif end > len(self._df) - 1:
      raise Exception("End index out of range")
    elif start < 0:
      raise Exception("Start index must be greater than or equal to 0")

    points = self._df.iloc[start:end + 1]
    startdate = points.iloc[0][self.get_date_col()]
    enddate = points.iloc[-1][self.get_date_col()]

    x_l = (enddate - startdate).total_seconds()
    nodv = -9999
    # y_n = y_0 + G(x_i / x_l)

    def f(row):
      if row[self.get_value_col()] != nodv:
        return row[self.get_value_col()] + (gap_width * ((row[self.get_date_col()] - startdate).total_seconds() / x_l))
      else:
        return row[self.get_value_col()]

    self._df.loc[points.index, self.get_value_col()] = points.apply(f, axis=1)

    return self._df
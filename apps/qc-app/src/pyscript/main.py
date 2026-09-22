print("==== Main thread ====")
import js

from edit_service import EditService, FilterOperation, ISO_FORMAT
from datetime import datetime
import json

print("==== Worker thread ====")

services = []

DATETIME_COL_INDEX = 0
VALUE_COL_INDEX = 1
QUALIFIER_COL_INDEX = 2

class edit_service_wrapper():
  def __init__(self, data) -> None:
    self.edit_service = EditService(json.loads(data))

  def get_data_frame(self):
    # https://www.jhanley.com/blog/pyscript-javascript-and-python-interoperability/
    # https://pyodide.org/en/stable/usage/api/python-api/ffi.html#
    return self.edit_service.get_dataframe()
  

  def persistence(self, times, range):
    return self.edit_service.persistence(times, range).index


  def find_gaps(self, time_value, time_unit, range):
    # Return index column
    return self.edit_service.find_gaps(time_value, time_unit, range).index


  def fill_gaps(self, gap, fill, interpolate_values, range):
    return self.edit_service.fill_gaps(gap, fill, interpolate_values, range)


  def delete_data_points(self, index):
    return self.edit_service.delete_points(index)


  def set_filter(self, filter: dict[FilterOperation, float]):
    filter = filter.to_py()

    # parse datetime: https://stackoverflow.com/questions/11893083/convert-normal-date-to-unix-timestamp
    # if filter[FilterOperation.START.value]:
    #   filter[FilterOperation.START.value] = datetime.fromtimestamp(filter[FilterOperation.START.value] / 1000)
      
    # if filter[FilterOperation.END.value]:
    #   filter[FilterOperation.END.value] = datetime.fromtimestamp(filter[FilterOperation.END.value] / 1000) 

    return self.edit_service.filter(filter).index


  def change_values(self, index_list, operator, value):
    self.edit_service.change_values(index_list.to_py(), operator, float(value))


  def add_points(self, points):
    points = points.to_py()
    for i, p in enumerate(points):
      points[i][0] = datetime.strptime(
        p[0], ISO_FORMAT)
      
      # extract qualifier codes
      points[i][2] = [q.code for q in p[2]['resultQualifiers']]

    return self.edit_service.add_points(points)


  def shift_points(self, index_list, time_value, time_unit):
    return self.edit_service.shift_points(index_list.to_py(), time_value, time_unit)


  def interpolate(self, index_list):
    return self.edit_service.interpolate(index_list.to_py())


  def drift_correction(self, start, end, gap_width):
    return self.edit_service.drift_correction(start, end, gap_width)


  def get_index_at(self, index):
    return self.edit_service.get_dataframe().index[index]


  def get_datetime_at(self, index):
    val = self.edit_service._df._mgr.arrays[DATETIME_COL_INDEX][0][index]
    return (val.value / 10 ** 6)


  def get_value_at(self, index):
    return self.edit_service._df._mgr.arrays[VALUE_COL_INDEX][0][index].item()
  

  def count(self):
    return len(self.get_data_frame().index)
  
  
  def get_date_column(self):
    timestamps = self.edit_service._df._mgr.arrays[DATETIME_COL_INDEX][0]
    return  [ts.value / 10 ** 6 for ts in timestamps]
  

  def get_value_column(self):
    values = self.edit_service._df._mgr.arrays[VALUE_COL_INDEX][0]
    return  [float(val) for val in values]
  
  
  def get_qualifier_column(self):
    values = self.edit_service._df._mgr.arrays[QUALIFIER_COL_INDEX][0]
    return [val for val in values]

js.edit_service_wrapper = edit_service_wrapper
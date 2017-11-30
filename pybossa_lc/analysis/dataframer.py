# -*- coding: utf8 -*-
"""Dataframer module (see https://github.com/Scifabric/enki)."""

import pandas


def create_data_frame(item):
    data = [explode_info(tr) for tr in item]
    index = [tr.__dict__['id'] for tr in item]
    return pandas.DataFrame(data, index)


def explode_info(item):
    item_data = item.__dict__
    protected = item_data.keys()
    if type(item.info) == dict:
        keys = item_data['info'].keys()
        for k in keys:
            if k in protected:
                item_data["_" + k] = item_data['info'][k]
            else:
                item_data[k] = item_data['info'][k]
    return item_data

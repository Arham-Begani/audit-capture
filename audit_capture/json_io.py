"""Strict JSON at all evidence entry points: reject ambiguous or non-finite inputs."""
import json


def loads(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError('Non-finite JSON number')

    return json.loads(data, object_pairs_hook=unique, parse_constant=nonfinite)

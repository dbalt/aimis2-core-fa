from enum import StrEnum


class FaServerAction(StrEnum):
    """Enum of supported actions for FaServer."""

    GET_DEVIATION_SUMMARY = 'get_deviation_summary'
    DELETE_METADATA = 'delete_metadata'
    SAVE_METADATA = 'save_metadata'
    GET_METADATA = 'get_metadata'
    DELETE_RESULTS = 'delete_results'
    DELETE_RESULTS_FOR_DT = 'delete_results_for_dt'

"""
Compute some featuers
"""


def add_death_columns(frame):

    frame.death_date = pd.DatetimeIndex(frame.death_date)

    # Was this person hospitalized
    frame["is_hospitalization"] = ~frame.hospitalization_in.isna()

    frame["T_is_dead"] = ~frame.death_date.isna()

    # The real discharge date
    frame["T_release_date"] = frame["discharge_date_max hospitalization_out".split()].max(axis=1)

    # Total time = ER + hospitalization
    frame["T_total_time_hospital"] = frame.release_date - frame.admission_date_min

    # Mortality of the ER
    frame["T_mortality_ER"] = frame.discharge_date_max >= frame.death_date

    # Mortality during hospitalization
    frame["T_mortality_hospitalization"] = (frame.release_date >= frame.death_date) & ~frame.mortality_ER

    #
    frame["T_mortality2d"] = frame.death_date <= frame.admission_date_min + pd.Timedelta('2d')
    frame["T_mortality30d"] = (frame.death_date <= frame.admission_date_min + pd.Timedelta('30d'))
    frame["T_mortality60d"] = (frame.death_date <= frame.admission_date_min + pd.Timedelta('60d'))

    return frame


if __name__ == "__main__":
    from shibaer.util import *
    data = load_pickle_files("DATAB", "ER")
    data = add_death_columns(data)
    print(data.head())
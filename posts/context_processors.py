import datetime as dt

def today(request):
    year = dt.datetime.today().year
    return {'year': year}
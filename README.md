# RTIR4REST
## Python Library for Request Tracker Incident Respose v/4 (RTIR) for automating Incidents. Beta2!

RTIR4REST is a simple Python library for handling Incident tickets in RTIR v/4 (RT for Incident Response by Best Practical) through the REST API interface. RTIR4REST uses Requests lib for handling the HTTP(S) Session connections. Proven under fire by handling more than 500K cases.
    
**Basic Usage**

rtir = RTIR4REST(usr,pwd,url)

rtir.login()

s = rtir.get_all_new_open_tickets()

print(s)

> 123: Incident Report #1

> 124: Incident Report #2

s = rtir.get_ticket_owner('123')

print(s)

> Nobody

rtir.take_ticket('123')

rtir.comment_ticket('123','Hello')

rtir.close_ticket('123')

rtir.logout()

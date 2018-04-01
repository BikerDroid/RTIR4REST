class RTIR4REST():
    # -*- coding: utf-8 -*-
    """
    RTIR4REST Library
    -----------------
    
    RTIR4REST is a simple Python library for handling Incident tickets in 
    RTIR v/4 (RT for Incident Response by Best Practical) through the REST API 
    interface.
    
    RTIR4REST uses Requests lib for handling the HTTP(S) Session connections.
    
    >>> Basic Usage <<<
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

    The following functions are available in this version:

    >>> OverView <<<
    login()
    logout()
    get_user_info(user)
    -
    get_all_nobody_tickets()
    get_all_new_open_tickets()
    get_all_new_open_tickets_idlist()
    -
    get_queue_info()
    get_all_queues():
    -
    get_ticket_info()
    get_ticket_item()
    get_ticket_status()
    get_ticket_status()
    get_ticket_owner()
    get_ticket_requestors()
    get_ticket_subject()
    get_ticket_ip()
    get_ticket_message()
    -
    take_ticket()
    steal_ticket()
    take_or_steal_ticket()
    -
    create_ticket()
    reply_ticket()
    comment_ticket()
    reopen_ticket()
    close_ticket()
    -
    take_comment_close_ticket()
    autocreate_ticket()
    
    Please see GitHub <https://github.com/BikerDroid/RTIR4REST> for further information.
    
    :copyright: BikerDroid (c) 2016-2018
    :license: Apache License 2.0 
    :Reference: https://rt-wiki.bestpractical.com/wiki/REST
    """

    #import asyncio
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    
    __title__     = 'RTIR4REST'
    __version__   = 'Beta 2.0.1'
    __build__     = 0x01042018
    __author__    = 'BikerDroid <bikerdroid@gmail.com>'
    __copyright__ = 'Copyright (c) 2016-2018, BikerDroid'

    def __init__(self,rtir_user,rtir_password,rtir_full_url,useragent='Mozilla/5.0.2018',proxy_dict={}):
        """Initializing RTIR4REST"""
        self.__loggedin = False
        self.__requests = self.requests
        self.__session = self.__requests.Session()
        self.__session.auth = (rtir_user, rtir_password)
        self.__session.headers = ({'User-Agent': useragent,'referer': rtir_full_url.rstrip('/')})
        self.__auth = {'user': rtir_user, 'pass': rtir_password}
        self.__rtir_base_url = rtir_full_url.rstrip('/')
        self.__rtir_cookie = ''
        self.__proxy = proxy_dict
        self.ticketcache = {}
        self.__ticket_items = ['id','Queue','Owner','Creator','Subject','Status','Priority',
                               'InitialPriority','FinalPriority','Requestors','Cc','AdminCc',
                               'Created','Starts','Started','Due','Resolved','Told',
                               'LastUpdated','TimeEstimated','TimeWorked','TimeLeft',
                               'CF.{Constituency}','CF.{How Reported}','CF.{Reporter Type}',
                               'CF.{IP}','CF.{Customer}','CF.{Classification}',
                               'CF.{Description}','CF.{Resolution}','CF.{Function}']

    def login(self):
        """Function: Login, Create Session, Get Cookie. Returns: True or False"""
        if not self.__loggedin:
            surl = self.__rtir_base_url
            try:
                r = self.__session.post(surl, data=self.__auth, verify=False, proxies=self.__proxy)
                if 'username or password is incorrect' in r.text:
                    print('*** Username or Password is incorrect ***')
                    self.__loggedin = False
                if '<title>Login</title>' in r.text:
                    print('*** Failed to Login ***')
                    self.__loggedin = False
                if '<title>RT at a glance</title>' in r.text:
                    self.__rtir_cookie = r.cookies
                    self.__loggedin = True                
            except Exception as e:
                print('> Error in login() :',e)
                self.__loggedin = False
        return self.__loggedin
    
    def newlogin(self,new_user,new_password):
        """Used to change current logged-in user to a new person"""
        self.logout()
        self.__session.auth = (new_user, new_password)
        self.__auth = {'user': new_user, 'pass': new_password}
        surl = self.__rtir_base_url
        try:
            r = self.__session.post(surl, data=self.__auth, verify=False, proxies=self.__proxy)
            if 'username or password is incorrect' in r.text:
                print('*** Username or Password is incorrect ***')
                self.__loggedin = False
            if '<title>Login</title>' in r.text:
                print('*** Failed to Login ***')
                self.__loggedin = False
            if '<title>RT at a glance</title>' in r.text:
                self.__rtir_cookie = r.cookies
                self.__loggedin = True                
        except Exception as e:
            print('> Error in login() :',e)
            self.__loggedin = False
        return self.__loggedin

    def logout(self):
        """Function: Clear Session and Cookie. Returns: True or False"""
        if self.__loggedin:
            surl = self.__rtir_base_url+'/REST/1.0/logout'
            params = ''
            payload = {'content': params}
            try:
                r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
                self.__session.close()
                self.__rtir_cookie = ''
                self.__loggedin = False
                self.__auth = None
                self.__session.auth = None
                return True
            except Exception as e:
                print('> Error in logout() :',e)
                return False

    def __rtir_text_format(self,intxt):
        """Function: Prepare text for RTIR Text (trailing space)"""
        s = intxt.strip()
        s = intxt.replace('\n','\n ')
        return s + '\n'

    def response_status(self,text):
        """Function: RTIR Status Response"""
        s = text.splitlines()[0].split(' ')
        rtir_version  = s[0].strip()
        status_code   = s[1].strip()
        status_string = s[2].strip()
        return [rtir_version,status_code,status_string]

    def clean_response(self,text):
        """Function: Remove first two lines of the RTIR response. #1: RT/4.2.9 200 Ok, #2: \n"""
        if len(text.splitlines()) > 2:
            return '\n'.join(text.splitlines()[2:]).strip()
        else:
            return text.strip()

    def search_tickets(self,query,raw=False):
        """Function: Search tickets using the RTIR search criteria. Query example: '(Created > "2016-01-01") AND (CF.{Classification} = "Spam")'"""
        if not self.__loggedin: return ''
        surl = self.__rtir_base_url+"/REST/1.0/search/ticket?query="+query
        try:
            r = self.__session.post(surl, verify=False, proxies=self.__proxy)
            if raw:
                return r.text.strip()
            else:
                s = ''
                if len(r.text.strip()):
                    for sline in r.text.strip().splitlines():
                        if ': ' in sline:
                            s += sline + '\n'
                    s = s[:-1]                    
                return s.strip()
        except Exception as e:
            print('> Error in get_all_new_open_tickets() :',e)
            return ''

    def get_all_nobody_tickets(self):
        """Function: Get UnOwned (Nobody), New and Open tickets. Returns: separated string."""
        if not self.__loggedin: return ''
        query = "(Owner='Nobody' AND (Status='new' OR Status='open'))"
        result = self.search_tickets(query)
        return result

    def get_all_new_open_tickets(self):
        """Function: Get all New and Open tickets of all users. Returns: separated string."""
        if not self.__loggedin: return ''
        query = "(Status='new' OR Status='open')"
        result = self.search_tickets(query)
        return result
        
    def get_all_new_open_tickets_idlist(self):
        """Get a ID list of new and open tickets of all users"""
        if not self.__loggedin: return []
        id_list = []
        scases = self.get_all_new_open_tickets()
        for sline in scases.splitlines():
            if ': ' in sline:
                id_list.append(sline.split(':')[0].strip())
        id_list.sort()
        return id_list

    def get_queue_info(self,queueid=''):
        """Get Queue information list (LF separated)."""
        if not self.__loggedin: return ''
        surl = self.__rtir_base_url+'/REST/1.0/queue/'+queueid
        try:
            r = self.__session.post(surl, verify=False, proxies=self.__proxy)
            s = ''
            if len(r.text.strip()):
                if 'does not exist' in r.text:
                    return ''
                else:
                    for sline in  r.text.strip().splitlines():
                        if ': ' in sline:
                            s += sline + '\n'
                    s = s[:-1]                    
                    return self.clean_response(s)
        except Exception as e:
            print('> Error in get_queue_info() :',e)
            return ''

    def get_all_queues(self,queue_id_max=16):
        """Get All Queues. Returns string: 'id,queue' + \n """
        if not self.__loggedin: return ''
        queues_list = ''
        for queueid in range(0,queue_id_max):
            surl = self.__rtir_base_url+'/REST/1.0/queue/'+str(queueid)
            r = self.__session.get(surl, verify=False, proxies=self.__proxy)
            for s in r.text.split('\n'):
                if 'Name:' in s:
                    try:
                        squeue = s.strip().split(': ')[1].strip()
                        if squeue:
                            queues_list += str(queueid)+','+squeue+'\n'
                    except:
                        pass
        return queues_list.strip()

    def get_user_info(self,user=''):
        """Get user information. Defaults to logged in user."""
        if not self.__loggedin: return ''
        if not len(user): 
            user = self.__auth['user']
        surl = self.__rtir_base_url+'/REST/1.0/user/'+user
        try:
            r = self.__session.post(surl, verify=False, proxies=self.__proxy)
            s = ''
            if len(r.text.strip()):
                for sline in  r.text.strip().splitlines():
                    if ': ' in sline:
                        s += sline + '\n'
                s = s[:-1]                    
            return s.strip()
        except Exception as e:
            print('> Error in get_user_info() :',e)
            return ''

    def get_ticket_info(self,sticketid,raw=False):
        """Get all information about the ticket."""
        if not self.__loggedin: return ''
        if not isinstance(sticketid,str): sticketid = str(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/show'
        try:
            if sticketid in self.ticketcache:
                response = self.ticketcache[sticketid]
            else:
                r = self.__session.post(surl, verify=False, proxies=self.__proxy)
                response = r.text.strip()
            if raw: return response
            s = ''
            if len(response):
                for sline in  response.splitlines():
                    if ': ' in sline:
                        s += sline + '\n'
                s = s[:-1]
            self.ticketcache.clear()
            self.ticketcache[sticketid] = s
            return s.strip()
        except Exception as e:
            self.ticketcache.clear()
            print('> Error in get_ticket_info() :',e)
            return ''

    def get_ticket_item(self,sticketid,ticketitem):
        """Get the ticket item. Valid ticketitems are in self.__ticket_items """
        if not self.__loggedin: return ''
        if not ticketitem.lower().strip() in [item.lower() for item in self.__ticket_items]: return ''
        lines = self.get_ticket_info(sticketid).splitlines()
        result = ''
        for s in lines:
            if ticketitem.lower().strip() in s.lower():
                if ': ' in s: result = ':'.join(s.split(':')[1:]).strip()
        return result

    def get_ticket_queue(self,sticketid):
        """Get ticket Queue (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'Queue')

    def get_ticket_status(self,sticketid):
        """Get ticket Status (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'Status')
 
    def get_ticket_owner(self,sticketid):
        """Get ticket owner (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'Owner')

    def get_ticket_creator(self,sticketid):
        """Get ticket Creator (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'Creator')

    def get_ticket_create_date(self,sticketid):
        """Get ticket Create Date (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'Created')

    def get_ticket_last_update(self,sticketid):
        """Get ticket Last Update Date (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'LastUpdated')

    def get_ticket_requestors(self,sticketid):
        """Get ticket Requestors (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'Requestors')
    
    def get_ticket_subject(self,sticketid):
        """Get ticket Subject (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'Subject')

    def get_ticket_ip(self,sticketid):
        """Get ticket IP (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'CF.{IP}')
    
    def get_ticket_classification(self,sticketid):
        """Get ticket Classification (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'CF.{Classification}')

    def get_ticket_constituency(self,sticketid):
        """Get ticket Classification (get_ticket_item helper)"""
        return self.get_ticket_item(sticketid,'CF.{Constituency}')
    
    def get_ticket_message(self,sticketid,content_type='text/plain'):
        """Get primary message (text/plain) for the ticket"""
        if not self.__loggedin: return ''
        if not isinstance(sticketid,str): sticketid = str(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/attachments'
        try:
            r = self.__session.post(surl, verify=False)
        except Exception as e:
            print('> Error in get_ticket_message(#1) :',e)
            return ''
        attachmentid = rawmessage = ''
        if len(r.text.strip()):
            for sline in  r.text.strip().splitlines():
                if content_type in sline:
                    x = 0
                    if 'attachments:' in sline.lower():
                        x = 1
                    attachmentid = sline.strip().split(':')[x].strip()
        if len(attachmentid):
            surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/attachments/'+attachmentid
            try:
                r = self.__session.post(surl, verify=False)
            except Exception as e:
                print('> Error in get_ticket_message(#2) :',e)
                return ''
            rawmessage = '\n'.join(r.text.splitlines()[2:]).strip()
        return rawmessage

    def get_ticket_message_id_list(self,sticketid,content_type='text/plain'):
        """Get message id list (text/plain) for the ticket"""
        if not self.__loggedin: return ''
        if not isinstance(sticketid,str): sticketid = str(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/attachments'
        try:
            r = self.__session.post(surl, verify=False, proxies=self.__proxy)
        except Exception as e:
            print('> Error in get_ticket_message(#1) :',e)
            return ''
        attachmentid = attachmentlist = ''
        if len(r.text.strip()):
            for sline in r.text.strip().splitlines():
                if content_type in sline:
                    x = 0
                    if 'attachments:' in sline.lower():
                        x = 1
                    attachmentid = sline.strip().split(':')[x].strip()
                    if len(attachmentid):
                        attachmentlist += attachmentid+','
        return attachmentlist[:-1]

    def get_ticket_message_by_id(self,sticketid,smessageid,content_type='text/plain'):
        """Get message by id for the ticket"""
        if not self.__loggedin: return ''
        if not isinstance(sticketid,str): sticketid = str(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/attachments/'+smessageid
        try:
            r = self.__session.post(surl, verify=False, proxies=self.__proxy)
        except Exception as e:
            print('> Error in get_ticket_message(#1) :',e)
            return ''
        if len(r.text.strip()):
            message = ''
            for sline in r.text.strip().splitlines():
                if 'RT/' in sline: continue
                message += sline+'\n'
        return message

    def take_ticket(self,sticketid):
        """Take UNowned ticket"""
        if not self.__loggedin: return ''
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/take'
        params = 'Action: take'
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return r.text.strip()
        except Exception as e:
            print('> Error in take_ticket() :',e)
            return ''

    def steal_ticket(self,sticketid):
        """Steal Owned ticket"""
        if not self.__loggedin: return ''
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/take'
        params = 'Action: steal'
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return r.text.strip()
        except Exception as e:
            print('> Error in steal_ticket() :',e)
            return ''

    def take_or_steal_ticket(self,sticketid):
        """Take or Steal ticket depending on ownership"""
        owner = self.get_ticket_owner(sticketid).lower().strip()
        user = self.__auth['user'].lower().strip()
        if 'nobody' in owner:
            self.take_ticket(sticketid)
        elif not user in owner:
            self.steal_ticket(sticketid)
        else:
            return

    def comment_ticket(self,sticketid,commenttext):
        """Create a internal Comment to the ticket"""
        if not self.__loggedin: return ''
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/comment'
        t_id = 'id: ' + sticketid + '\n'
        action = 'Action: comment\n'
        text = 'Text: ' + self.__rtir_text_format(commenttext)
        params = t_id + action + text
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return r.text.strip()
        except Exception as e:
            print('> Error in comment_ticket() :',e)
            return ''

    def create_ticket(self,abusemail,subj,bodytxt,constituency='',cc='',admincc=''):
        """Create a new ticket with basic data. Use bodytext='' to autocreate_ticket(). The abuseemail is the Correspondents"""
        if not self.__loggedin: return ''
        surl = self.__rtir_base_url+'/REST/1.0/ticket/new'
        ecc = eadmincc = sip = sconstituency = ''
        t_id = 'id: ticket/new\n'
        queue = 'Queue: Incident Reports\n'
        owner = 'Owner: ' + self.__auth['user'] + '\n'
        requestor = 'Requestor: ' + abusemail.strip() + '\n'
        subject = 'Subject: ' + subj.strip() + '\n'
        text = 'Text: ' + self.__rtir_text_format(bodytxt)
        customer = 'CF-Customer: ' + abusemail.strip() + '\n'
        reporter_type = 'CF-Reporter Type: External\n'
        if len(constituency):
            sconstituency = 'CF-Constituency: ' + constituency + '\n'
        if len(cc):
            ecc = 'Cc: ' + cc.strip() + '\n'
        if len(admincc):
            eadmincc = 'AdminCc: ' + admincc.strip() + '\n'
        params = t_id + queue + requestor + owner + ecc + eadmincc + subject + text + customer + reporter_type + ecc + eadmincc
        payload = {'content': params}        
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            sticket = r.text.strip().splitlines()[2].split(' ')[2] # '# Ticket 888888 created.'
            return sticket.strip()  
        except Exception as e:
            print('> Error in create_ticket() :',e)
            return ''

    def set_ticket_owner(self,sticketid,owner):
        """Set the owner of the ticket. Must be a valid user."""
        if not self.__loggedin: return ''
        self.take_or_steal_ticket(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/edit'
        t_id = 'id: ' + sticketid + '\n'
        sowner = 'Owner: ' + owner + '\n'
        params = t_id + sowner
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return self.clean_response(r.text)
        except Exception as e:
            print('> Error in set_ticket_owner() :',e)
            return ''

    def set_ticket_resolution(self,sticketid,resolution):
        """Set the resolution of the ticket. Queue = Incidents"""
        if not self.__loggedin: return ''
        self.take_or_steal_ticket(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/edit'
        sresolution = 'CF-Resolution: ' + resolution + '\n'
        params = sresolution
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return self.clean_response(r.text)
        except Exception as e:
            print('> Error in set_ticket_resolution() :',e)
            return ''

    def set_ticket_queue(self,sticketid,queue):
        """Set Queue"""
        if not self.__loggedin: return ''
        self.take_or_steal_ticket(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/edit'
        squeue = 'Queue: ' + queue + '\n'
        params = squeue
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return self.clean_response(r.text)
        except Exception as e:
            print('> Error in reopen_ticket() :',e)
            return ''

    def set_ticket_classification(self,sticketid,classification):
        """Update ticket classification"""
        if not self.__loggedin: return ''
        self.take_or_steal_ticket(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/edit'
        queue = 'Queue: Incidents\n'
        sclassification = 'CF-Classification: ' + classification
        params = queue + sclassification
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return self.clean_response(r.text)
        except Exception as e:
            print('> Error in reopen_ticket() :',e)
            return ''

    def set_ticket_ip(self,sticketid,ipaddress):
        """Update ticket IP-address"""
        if not self.__loggedin: return ''
        self.take_or_steal_ticket(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/edit'
        queue = 'Queue: Incidents\n'
        ip = 'CF-IP: ' + ipaddress
        params = queue + ip
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return self.clean_response(r.text)
        except Exception as e:
            print('> Error in reopen_ticket() :',e)
            return ''

    def reply_ticket(self,sticketid,bodytext,cc='',bcc=''):
        """Create a reply and send to requesters via RTIR"""
        if not self.__loggedin: return ''
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/comment'
        ecc = ebcc = ''
        t_id = 'id: ' + sticketid + '\n'
        action = 'Action: correspond\n'
        text = 'Text: ' + self.__rtir_text_format(bodytext)
        if len(cc):
            ecc = 'Cc: ' + cc.strip() + '\n'
        if len(bcc):
            ebcc = 'Bcc: ' + bcc.strip() + '\n'
        params = t_id + action + text + ecc + ebcc
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return r.text.strip()
        except Exception as e:
            print('> Error in reply_ticket() :',e)
            return ''

    def reopen_ticket(self,sticketid):
        """Update ticket status to open"""
        if not self.__loggedin: return ''
        self.take_or_steal_ticket(sticketid)
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/edit'
        params = 'Status: open'
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return self.clean_response(r.text)
        except Exception as e:
            print('> Error in reopen_ticket() :',e)
            return ''

    def close_ticket(self,sticketid):
        """Update ticket to Resolved (closed)"""
        if not self.__loggedin: return ''
        surl = self.__rtir_base_url+'/REST/1.0/ticket/'+sticketid+'/edit'
        params = 'Status: resolved'
        payload = {'content': params}
        try:
            r = self.__session.post(surl, data=payload, verify=False, proxies=self.__proxy)
            return self.clean_response(r.text)
        except Exception as e:
            print('> Error in close_ticket() :',e)
            return ''

    def take_comment_close_ticket(self,sticketid,comment):
        """Take/Steal, Comment, and Close the Ticket."""
        self.take_or_steal_ticket(sticketid)
        self.comment_ticket(sticketid,comment)
        return self.close_ticket(sticketid)
    
    def take_comment_classify_close_ticket(self,sticketid,comment,classification):
        """Take/Steal, Comment, Classify, and Close the Ticket."""
        self.take_or_steal_ticket(sticketid)
        self.comment_ticket(sticketid,comment)
        self.set_ticket_queue(sticketid,'Incidents')
        self.set_ticket_classification(sticketid,classification)
        return self.close_ticket(sticketid)
    
    def take_reply_comment_classify_close_ticket(self,sticketid,bodytext,comment,classification):
        """Take/Steal, Comment, Classify, and Close the Ticket."""
        self.take_or_steal_ticket(sticketid)
        self.reply_ticket(sticketid,bodytext)
        self.comment_ticket(sticketid,comment)
        self.set_ticket_queue(sticketid,'Incidents')
        self.set_ticket_classification(sticketid,classification)
        return self.close_ticket(sticketid)

    def autocreate_ticket(self,email,subject,abusetext,comment,ipaddress,classification):
        """Create, Reply, Comment, set Incidents as Queue, Classify, Set IP-address, and Close a ticket in one go."""
        if not self.__loggedin: return ''
        sticketid = self.create_ticket(email,subject,'')
        if len(sticketid):
            self.reply_ticket(sticketid,abusetext)
            self.comment_ticket(sticketid,comment)
            self.set_ticket_queue(sticketid,'Incidents')
            self.set_ticket_classification(sticketid,classification)
            self.set_ticket_ip(sticketid,ipaddress)
            self.close_ticket(sticketid)
        return sticketid
## End Class

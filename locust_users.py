
import re,time,json
import subprocess
import gevent
import websocket
from locust import User,HttpUser

class WebSocketUser(HttpUser):
    '''
    if test need request https? api  and link wss? api.
    this user may be help you for your pressure-testing.
    and my english is not good,so sad.
    '''

    abstract = True

    def __init__(self, parent,expect_recv_msg=''):
        super().__init__(parent)
        self.msg_box = []  
        self.expect_recv_msg = expect_recv_msg
    
    def on_message(self, ws, message):
        if self.expect_recv_msg in message:
            response_time= int(round(time.monotonic() - self.send_time,3)*10000)
            self.environment.events.request_success.fire(
            request_type="WSR",
            name="recieved result msg",
            response_time=response_time,
            response_length=len(message)
            )
            ws.send(json.dumps({'data':"exit\r\n"}))
            self.on_close(ws)

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws):
        pass

    def on_open(self,ws):
        body = json.dumps({'data':"id\r\n"})
        ws.send(body)
        self.send_time = time.monotonic()
        self.environment.events.request_success.fire(
            request_type="WSS",
            name="sent",
            response_time=None,
            response_length=len(body)
            )

    def connectApp(self,ws_url,timeout=20,**kwargs):
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            **kwargs
        )
        gevent.spawn(self.ws.run_forever).join(timeout=timeout)



class SSHUser(User):

    '''
    if your testing target is ssh server, use it.
    '''

    abstract = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def test(self,user='',scmd='',expect='',timeout=20):
        try:
            t0 = time.monotonic() 
            if user:
                user = "%s@" %user
            cmd = "bash -c \"ssh {user}{host} \'{scmd}\'\"".format(
                user=user,
                host=self.host,
                scmd=scmd
            )
            name = "ready to connect {user}@{host} and send {cmd}".format(
                user=user,
                host=self.host,
                scmd=scmd
            )
            self.environment.events.request_success.fire(
                        request_type="SSHC",
                        name=name,
                        response_time=None,
                        response_length=len(cmd)
                    )
            with subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE,
                shell=True
            ) as p: 
                if p.stdout.read() == expect:
                    self.environment.events.request_success.fire(
                        request_type="SSHR",
                        name="recv %s" % expect,
                        response_time=int(round(time.monotonic() -  t0,3)*10000),
                        response_length=len(expect)
                    )
                p.communicate(timeout=timeout)
                p.kill()
        except OSError as e:
            self.environment.events.request_failure.fire(
                    request_type="SSHR",
                    name="error",
                    response_time=int(round(time.monotonic() -  t0,3)*10000),
                    response_length=0,
                    exception=e
                )
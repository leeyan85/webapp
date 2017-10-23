#-*- coding:utf-8 -*- 
from django.shortcuts import render_to_response,render,redirect,get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect  
from django.contrib.auth.models import User  
from django.contrib import auth 
from django.contrib import messages
from django.template.context import RequestContext
from django.forms.formsets import formset_factory
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from bootstrap_toolkit.widgets import BootstrapUneditableInput
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .forms import LoginForm
from django import forms
import models
import json
import os,sys
import actions

def RunCommandOnAnsible(command):
    ansible_primary_server='10.75.30.29'
    ansible_user='letv'
    ansible_password='leshiVM1404'
    server=actions.Server(host=ansible_primary_server, port=22, username=ansible_user, password=ansible_password)    
    result=server.execute(command)
    return result    

def send_email(subject,content,receiver):
    sender="SEE@le.com"
    command='cd /letv/scripts/report/;python mail.py \"%s\" \"%s\" \"%s\" \"%s\"' %(subject,content,sender,receiver)
    RunCommandOnAnsible(command)

def CheckOwnerIP(request,ipaddr):
    email_suffix=u'@le.com'
    user = getattr(request, 'user', None)
    useremail=user.username+email_suffix
    hosts_inventory=models.HostInventory.objects.filter(contact=useremail)
    hosts={}
    for host in hosts_inventory:
        ip=models.Interface.objects.get(hostid=host.hostid)
        hosts[host]=ip
        if ip.ip==ipaddr:
            ownerright=True
            break
        else:
            ownerright=False
            continue
    return ownerright

def GetOwnerIP(request):
    email_suffix=u'@le.com'
    user = getattr(request, 'user', None)
    useremail=user.username+email_suffix
    hosts_inventory=models.HostInventory.objects.filter(contact=useremail)
    hosts={}
    for host in hosts_inventory:
        ip=models.Interface.objects.get(hostid=host.hostid)
        hosts[host]=ip
    return hosts,user

@csrf_exempt
def login2(request):
    if request.user.is_authenticated():
        return redirect('/webapp/devself/home/')
    if request.method == 'GET':
        form = LoginForm()
        next_url=request.GET.get('next')
        return render_to_response('devself/sign-in.html', RequestContext(request, {'loginform': form,'next':next_url}))
    else:
        form = LoginForm(request.POST)
        if form.is_valid():
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')
            next_url = request.POST.get('next', '')
            user = auth.authenticate(username=username, password=password)
            if user is not None and user.is_active:
                auth.login(request, user)
                print 'asdfasfd',next_url,type(next_url)
                #print request.session
                if next_url == "":
                    print "hello"
                    return redirect('/webapp/devself/home/')
                elif next_url=="None":
                    print "none"
                    return redirect('/webapp/devself/home/')
                else:
                    return redirect(next_url)
            else:
                print "password is not right"
                return render_to_response('devself/sign-in.html', RequestContext(request, {'loginform': form,'LoginStatus':'username/password is wrong','next':''}))
        else:
            print "form is not valid"
            next_url = request.POST.get('next', '')
            return render_to_response('devself/sign-in.html', RequestContext(request, {'loginform': form,'next':''})) 

                
@login_required
@csrf_exempt
def home(request):
    hosts,user=GetOwnerIP(request)
    Mutihosts=1
    return render_to_response('devself/home.html',RequestContext(request, {'username': user,'vms':hosts,'Mutihosts':Mutihosts}))



@login_required
@csrf_exempt
def ModifyVmPassword(request,ipaddress):
    class RegularForm(forms.Form):    
        ipaddr = forms.CharField(
                required=True,
                label="IP Address",
                error_messages={'required': 'please input the ipaddress'},
                widget=forms.TextInput(
                    attrs={
                        'placeholder':"",
                        'class':"form-control span12",
                        'value': ipaddress,
                    }
                ),
        ) 
        def clean(self):
            if not self.is_valid():
                raise forms.ValidationError("IP and password are required")
            else:
                cleaned_data = super(RegularForm, self).clean()
                
    user = getattr(request, 'user', None)
    button_value='Reset'
    if request.method=="GET":
        #RegularForm.ipaddr.widget.update({'value': ipaddress })
        info="Click Reset button, the password of VNC,samba,system account will be reset unified, you will receive a random password by email from SEE@le.com, you can run command \"vmcfg\" to modify the password by yourself."
        form = RegularForm()
        ret_dic={'changpasswd':form,'function_name':'Modify VM password','username': user,'info':info,'button_value':button_value}
        return render_to_response('devself/function.html',RequestContext(request,ret_dic))
    else:
        form = RegularForm(request.POST)
        if form.is_valid():
            ipaddr=request.POST.get('ipaddr')
            user = getattr(request, 'user', None)
            ownerright=CheckOwnerIP(request,ipaddr)            
            if ownerright:
                command="cd /letv/scripts/assign_vm;python reset_password.py %s"%ipaddr
                result=RunCommandOnAnsible(command)
                random_password=result['out'][-1].strip('\n')
                print random_password
                email_suffix='@le.com'
                print user.username
                useremail=user.username+email_suffix
                subject='VM random password of %s'%ipaddr
                content="the random password of VNC,samba and system account \'andbase\' is \'%s\', you can run command \'vmcfg\' to modify the password unified"%random_password
                print  subject,content,useremail             
                send_email(subject,content,useremail)
                info="Reset vm %s password sucessfully, please get the passowrd through email, sender is SEE@le.com" %ipaddr
                title="Reset password successfully"
                return render_to_response('devself/functionOK.html', RequestContext(request,{'username':user,'ipaddress':ipaddr,'info':info,'title':title}))
            else:
                return render_to_response('devself/vmOwnerWrong.html', RequestContext(request,{'username':'user','ipaddress':ipaddr}))
            
        else:
            ret_dic={'username':'user','function_name':'Modify VM password','changpasswd':form,'button_value':button_value}
            return render_to_response('devself/function.html', RequestContext(request, ret_dic)) 

@login_required
@csrf_exempt
def ModifyVmPassword2(request,ipaddress):    
    if request.method=="GET":
        ret_dic={'ipaddr':ipaddress,'function_name':'Modify VM password'}
        return render_to_response('devself/function2.html',RequestContext(request,ret_dic))
    else:
        form = RegularForm(request.POST)
        if form.is_valid():
            print "hello,world"
        else:
            ret_dic={'function_name':'Modify VM password','changpasswd':form}
            return render_to_response('devself/function2.html', RequestContext(request, ret_dic))
        
@login_required
@csrf_exempt           
def restartvnc(request,ipaddress):
    class RegularForm(forms.Form):    
        ipaddr = forms.CharField(
                required=True,
                label="IP Address",
                error_messages={'required': 'please input the ipaddress'},
                widget=forms.TextInput(
                    attrs={
                        'placeholder':"",
                        'class':"form-control span12",
                        'value': ipaddress,
                    }
                ),
        ) 
        def clean(self):
            if not self.is_valid():
                raise forms.ValidationError("IP and password are required")
            else:
                cleaned_data = super(RegularForm, self).clean()
                
    user = getattr(request, 'user', None)
    button_value='Restart'
    if request.method=="GET":
        #RegularForm.ipaddr.widget.update({'value': ipaddress })
        info="Click Restart button, VNC service will be restarted to fix the issue that you can't input anything when you use VNC"
        form = RegularForm()
        ret_dic={'changpasswd':form,'function_name':'Restart VNC service','username': user,'info':info,'button_value':button_value}
        return render_to_response('devself/function.html',RequestContext(request,ret_dic))
    else:
        form = RegularForm(request.POST)
        if form.is_valid():
            ipaddr=request.POST.get('ipaddr')
            user = getattr(request, 'user', None)
            ownerright=CheckOwnerIP(request,ipaddr)            
            if ownerright:
                info="VM %s restart VNC service successfull, three default opened ports are 10,11,12."%ipaddr
                title="Restart VNC successfully"
                command='cd /letv/scripts/ansible/api;python ansible_api_v2.py %s' %ipaddr
                print command
                RunCommandOnAnsible(command)
                return render_to_response('devself/functionOK.html', RequestContext(request,{'username':user,'ipaddress':ipaddr,'info':info,'title':title}))
            else:
                return render_to_response('devself/vmOwnerWrong.html', RequestContext(request,{'username':'user','ipaddress':ipaddr}))
            
        else:
            ret_dic={'username':'user','function_name':'Restart VNC service','changpasswd':form,'button_value':button_value}
            return render_to_response('devself/function.html', RequestContext(request, ret_dic)) 

@csrf_exempt
@login_required
def mountnfs(request,ipaddress):
    class RegularForm(forms.Form):    
        ipaddr = forms.CharField(
                required=True,
                label="IP Address",
                error_messages={'required': 'please input the ipaddress'},
                widget=forms.TextInput(
                    attrs={
                        'placeholder':"",
                        'class':"form-control span12",
                        'value': ipaddress,
                    }
                ),
        ) 
        def clean(self):
            if not self.is_valid():
                raise forms.ValidationError("IP and password are required")
            else:
                cleaned_data = super(RegularForm, self).clean()
                
    user = getattr(request, 'user', None)
    button_value='Mount'
    if request.method=="GET":
        #RegularForm.ipaddr.widget.update({'value': ipaddress })
        info="Click Mount button, NFS disk will be mounted under /le_data"
        form = RegularForm()
        ret_dic={'changpasswd':form,'function_name':'Mount NFS disk','username': user,'info':info,'button_value':button_value}
        return render_to_response('devself/function.html',RequestContext(request,ret_dic))
    else:
        form = RegularForm(request.POST)
        if form.is_valid():
            ipaddr=request.POST.get('ipaddr')
            user = getattr(request, 'user', None)
            ownerright=CheckOwnerIP(request,ipaddr)
            if ownerright:
                command="cd /letv/scripts/mount_space;python remote_mount_space.py %s"%ipaddr
                RunCommandOnAnsible(command)
                info="VM %s mount NFS successfully on"  %ipaddr
                title="Mount NFS successfully"                
                return render_to_response('devself/functionOK.html', RequestContext(request,{'username':user,'ipaddress':ipaddr,'info':info,'title':title}))
            else:
                return render_to_response('devself/vmOwnerWrong.html', RequestContext(request,{'username':'user','ipaddress':ipaddr}))
            
        else:
            ret_dic={'username':'user','function_name':'Mount NFS disk','changpasswd':form,'button_value':button_value}
            return render_to_response('devself/function.html', RequestContext(request, ret_dic))   


@csrf_exempt
@login_required
def restoreserver(request,ipaddress):              
    class RegularForm(forms.Form):    
        ipaddr = forms.CharField(
                required=True,
                label="IP Address",
                error_messages={'required': 'please input the ipaddress'},
                widget=forms.TextInput(
                    attrs={
                        'placeholder':"",
                        'class':"form-control span12",
                        'value': ipaddress,
                    }
                ),
        ) 
        def clean(self):
            if not self.is_valid():
                raise forms.ValidationError("IP and password are required")
            else:
                cleaned_data = super(RegularForm, self).clean()                
    user = getattr(request, 'user', None)
    button_value='Restore'
    if request.method=="GET":
        #RegularForm.ipaddr.widget.update({'value': ipaddress })
        info="Every day, we will backup the /home/andbase directory, in case you delete your configure, or your VM is reset. Click Resotre button, you can restore it from backup"
        form = RegularForm()
        ret_dic={'changpasswd':form,'function_name':'Restore home dir','username': user,'info':info,'button_value':button_value}
        return render_to_response('devself/function.html',RequestContext(request,ret_dic))
    else:
        form = RegularForm(request.POST)
        if form.is_valid():
            ipaddr=request.POST.get('ipaddr')
            user = getattr(request, 'user', None)
            ownerright=CheckOwnerIP(request,ipaddr)
            if ownerright:
                command="cd /letv/scripts/Backup-recovery;python reduction.py %s %s"%(ipaddr,ipaddr)
                RunCommandOnAnsible(command)
                info="Restore your /home/andbase on %s"  %ipaddr
                title="Restore successfully"                
                return render_to_response('devself/functionOK.html', RequestContext(request,{'username':user,'ipaddress':ipaddr,'info':info,'title':title}))
            else:
                return render_to_response('devself/vmOwnerWrong.html', RequestContext(request,{'username':'user','ipaddress':ipaddr}))
            
        else:
            ret_dic={'username':'user','function_name':'Restore home dir','changpasswd':form,'button_value':button_value}
            return render_to_response('devself/function.html', RequestContext(request, ret_dic))  

@csrf_exempt
@login_required
def keepserver(request,ipaddress):
    class RegularForm(forms.Form):
        ipaddr = forms.CharField(
                required=True,
                label="IP Address",
                error_messages={'required': 'please input the ipaddress'},
                widget=forms.TextInput(
                    attrs={
                        'placeholder':"",
                        'class':"form-control span12",
                        'value': ipaddress,
                    }
                ),
        )
        def clean(self):
            if not self.is_valid():
                raise forms.ValidationError("IP and password are required")
            else:
                cleaned_data = super(RegularForm, self).clean()
    user = getattr(request, 'user', None)
    button_value='keep'
    if request.method=="GET":
        #RegularForm.ipaddr.widget.update({'value': ipaddress })
        info="click keep button, your vm will not be recycled"
        form = RegularForm()
        ret_dic={'changpasswd':form,'function_name':'keep server','username': user,'info':info,'button_value':button_value}
        return render_to_response('devself/function.html',RequestContext(request,ret_dic))
    else:
        form = RegularForm(request.POST)
        if form.is_valid():
            ipaddr=request.POST.get('ipaddr')
            user = getattr(request, 'user', None)
            ownerright=CheckOwnerIP(request,ipaddr)
            if ownerright:
                hostname='vm-'+ipaddr.replace('.','-')
                host_inventory=models.HostInventory.objects.get(hostid__name=hostname)
                host_inventory.date_hw_expiry=''
                host_inventory.save()
                command="/usr/bin/zabbix_sender -s %s -c /etc/zabbix/zabbix_agentd.conf -k check.vm.util.trapper -o 1" %hostname
                info="keep your VM successfully %s"  %ipaddr
                output=os.popen(command)
                print output.read()
                title="keep server successfully"
                return render_to_response('devself/functionOK.html', RequestContext(request,{'username':user,'ipaddress':ipaddr,'info':info,'title':title}))
            else:
                return render_to_response('devself/vmOwnerWrong.html', RequestContext(request,{'username':'user','ipaddress':ipaddr}))

        else:
            ret_dic={'username':'user','function_name':'keep Server','changpasswd':form,'button_value':button_value}
            return render_to_response('devself/function.html', RequestContext(request, ret_dic))

    
@login_required
@csrf_exempt
def logout(request):
    auth.logout(request)
    return redirect('/webapp/devself/accounts/login2')

import click, configparser, json, requests, time
from os.path import expanduser, join, isfile
from os import getcwd
from render import render

config = configparser.ConfigParser()
config_loc = join(expanduser('~'),'.darth-vdr.ini')
config.read(config_loc)

default = 'default' # Different configs
base_url = 'http://virtu-publi-1ia4y4za6rj1t-1399708161.us-east-1.elb.amazonaws.com/vdr'

try:
    user_fiuid = config.get(default,'fiuid')
except:
    config.add_section(default)
    config.set(default,'fiuid','')
    with open(config_loc, 'w') as f:
        config.write(f)
    user_fiuid = ''

def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError as e:
    return False
  return True

@click.group()
def cli1():
    """ This CLI does requires authentication"""
    pass

@cli1.command()
@click.option("--fiuid",prompt="FIU ID",help="Your FIU ID received from Darth VDR")
def login(fiuid):
    config.set(default,'fiuid',fiuid)
    with open(config_loc, 'w') as f:
        config.write(f)
    click.echo("Welcome to Darth VDR CLI!")
    print(render('logo2.png'))
    click.echo("Use `darth-vdr create` to create your first function!")

def checkLoginState(ctx, param, value):
    if not value:
        click.echo('You need to login to continue, use ',nl='')
        click.secho('`darth-vdr login`',bold=True,nl='')
        click.echo('or use the flag --fiuid ')
        ctx.exit()
    return value

@cli1.command()
@click.option('--fiuid',help="Your FIU ID received from Darth VDR",default=user_fiuid,callback=checkLoginState,is_eager=True,expose_value=False)
@click.option('--name',prompt="Function Name",help="The name of the function you want to create")
@click.option('--id',default='new',help="The id of the function. Used for updation")
@click.option('--handler',prompt="Handler",help="The location of handler function (Eg. index.handle)")
@click.option('--runtime',prompt="Runtime",help="The runtime engine to use.", type=click.Choice(["nodejs","nodejs4.3","nodejs6.10","nodejs8.10","nodejs10.x","nodejs12.x","java8","java11","python2.7","python3.6","python3.7","python3.8","dotnetcore1.0","dotnetcore2.0","dotnetcore2.1","dotnetcore3.1","nodejs4.3-edge","go1.x","ruby2.5","ruby2.7"], case_sensitive=False))
@click.option('--zip',prompt="Zip Location",help="The location of zip file", type=click.Path(exists=False))
def create(**data):
    with open(join(getcwd(),'darth-vdr.json'), 'w') as out:
        json.dump(data,out,indent=4, sort_keys=True)
        click.echo("Created your darth-vdr.json file!")
        try: # Error here
            with open('function.schema.json', 'x') as fw:
                json.dumps({"$schema": "http://json-schema.org/draft-07/schema#"},fw,indent=4,sort_keys=False)
                click.echo("Created your function.schema.json")
        except:
            click.echo("function.schema.json already exists and has not been modified.")


def fnStatus(fnid):
    l = 12
    with click.progressbar(length = l, label="Deployment Progress") as bar:
        for x in range(1,l):
            bar.update(x)
            time.sleep(10)
            url = base_url + '/getFunctionDetails'
            r = requests.get(url, params={'functionId': fnid})
            if r.status_code == 200:
                data = r.json()
                if data['functions'][fnid]['state'] == 'ACTIVE' or data['functions'][fnid]['state'] == 'INACTIVE':
                    bar.update(l)
                    click.secho("\nDeployment Successful!",fg="green")
                    return
                elif data['functions'][fnid]['state'] == "FAILED":
                    bar.update(l)
                    click.secho("\nDeployment Failed!",fg="red")
                    return
    click.secho("Deployment taking way too long.",fg="yellow")

@cli1.command()
@click.option('--fiuid',help="Your FIU ID received from Darth VDR",default=user_fiuid,callback=checkLoginState,is_eager=True)
@click.option('--configFile',help="The location of configuration file",default='darth-vdr.json',type=click.Path(exists=True,readable=True))
def deploy(fiuid,configfile):
    with open(configfile, 'r+') as c:
        data = json.load(c)
        if data['id'] == 'new':
            url = base_url + "/createFunction"
            files = [
                ('function', open(join(getcwd(),data["zip"]),'rb'))
            ]
            schema = ''
            with open("function.schema.json", "r") as lst:
                schema = lst.read()
            if not is_json(schema):
                click.secho("Invalid Schema", fg="red")
                return
            payload = {
                'fiuId': fiuid,
                'jsonSchema': schema,
                'handler': data['handler'],
                'runtime': data['runtime'],
                'functionName': data['name']
            }
            r = requests.request("POST", url, headers={}, data = payload, files=files)
            if r.status_code != 200 and r.status_code != 202:
                click.secho("Function could not be created!",fg="red")
                # print(r.text.encode('utf8'))
                # print(r.content)
                # print(r.status_code)
                # print(r.request.body)
                # print(r.request.headers)
            else:
                fn = r.json()
                data['id'] = fn['functionId']
                c.seek(0)
                json.dump(data,c,indent=4, sort_keys=True)
                c.truncate()

                click.secho("Function packed and uploaded!",fg="green")
                click.secho("Starting deployment on Darth VDR!")
                fnStatus(data['id'])

        else:
            url = base_url + "/updateFunction/" + str(data['id'])
            files = [
                ('function', open(join(getcwd(),data["zip"]),'rb'))
            ]
            schema = ''
            with open("function.schema.json", "r") as lst:
                schema = lst.read()
            
            if not is_json(schema):
                click.secho("Invalid Schema", fg="red")
                return
            payload = {
                'fiuId': fiuid,
                'jsonSchema': schema,
                'handler': data['handler'],
                'runtime': data['runtime'],
                'functionName': data['name']
            }
            r = requests.request("PUT", url, headers={}, data = payload, files=files)
            if r.status_code != 200 and r.status_code != 202:
                click.secho("Function could not be update!",fg="red")
                print(r.text)
                # print(r.text.encode('utf8'))
                # print(r.content)
                # print(r.status_code)
                # print(r.request.body)
                # print(r.request.headers)
                # print(r.request)
            else: 
                click.secho("Function packed and uploaded!",fg="yellow")
                click.secho("Updating deployment on Darth VDR!")
                fnStatus(data['id'])

@cli1.command()
@click.option('--fiuid',help="Your FIU ID received from Darth VDR",default=user_fiuid,callback=checkLoginState,is_eager=True)
@click.option('--configFile',help="The location of configuration file",default='darth-vdr.json',type=click.Path(exists=True,readable=True))
def status(fiuid,configfile):
    with open(configfile, 'r+') as c:
        con = json.load(c)
        if con['id'] == 'new':
            click.echo("Function not yet deployed! Use `darth-vdr deploy` to deploy!")
            return
        click.echo(f'Getting deployment status of function {con.get("id")}')
        url = base_url + '/getFunctionDetails'
        r = requests.get(url, params={'functionId': con['id']})
        if r.status_code == 200:
            data = r.json()
            if data['functions'][con['id']]['state'] == 'ACTIVE' or data['functions'][con['id']]['state'] == 'INACTIVE':
                click.secho("Deployment Successful!",fg="green")
            elif data['functions'][con['id']]['state'] == "FAILED":
                click.secho("Deployment Failed!",fg="red")
            elif data['functions'][con['id']]['state'] == "PENDING":
                click.secho("Deployment Pending!",fg="yellow")
            else:
                click.echo("Error while checking!")

@cli1.command('list-functions')
@click.option('--fiuid',help="Your FIU ID received from Darth VDR",default=user_fiuid,callback=checkLoginState,is_eager=True)
def listFn(fiuid):
    click.echo(f'Getting all functions for FIU {fiuid}')
    url = base_url + '/getFunctionsByFiuId'
    r = requests.get(url, params={'fiuId': fiuid})
    if r.status_code == 200:
        data = r.json()
        for fnx in data['functions']:
            fn = data['functions'][fnx]
            if fn['state'] == 'ACTIVE' or fn['state'] == 'INACTIVE':
                click.secho("ACTIVE",fg="green", nl=False)
            elif fn['state'] == 'FAILED':
                click.secho("FAILED", fg="red", nl=False)
            elif fn['state'] == 'PENDING':
                click.secho("PENDING", fg="yellow", nl=False)
            click.echo(f'\t{fn["functionName"]} ({fn["functionId"]})')

@cli1.command('list-jobs')
@click.option('--fiuid',help="Your FIU ID received from Darth VDR",default=user_fiuid,callback=checkLoginState,is_eager=True)
def listFn(fiuid):
    click.echo(f'Getting all jobs for FIU {fiuid}')
    url = base_url + '/getJobsByFiuId'
    r = requests.get(url, params={'fiuId': fiuid})
    if r.status_code == 200:
        data = r.json()
        for fnx in data['jobs']:
            jb = data['jobs'][fnx]
            if jb['state'] == 'SUCCESS':
                click.secho("SUCCESS",fg="green", nl=False)
            elif jb['state'] == 'FAILED':
                click.secho("FAILED", fg="red", nl=False)
            elif jb['state'] == 'PROCESSING':
                click.secho("PROCESSING", fg="yellow", nl=False)
            elif jb['state'] == 'CREATED':
                click.secho("CREATED", fg="yellow", nl=False)
            click.echo(f'\t{jb["jobId"]} (Function: {jb["functionId"]})')


# darth job latest
# darth job 452-235-245
# darth-vdr create-job
def jbStatus(fnid):
    l = 8
    with click.progressbar(length = l, label="Job Running") as bar:
        for x in range(1,l):
            bar.update(x)
            time.sleep(15)
            url = base_url + '/getJobDetails'
            r = requests.get(url, params={'jobId': fnid})
            if r.status_code == 200:
                data = r.json()

                if data['jobs'][fnid]['state'] == 'SUCCESS':
                    bar.update(l)
                    click.secho("\nJob ran successfully",fg="green")
                    rx = json.loads(data['jobs'][fnid]['result'])
                    print("Result", rx['data'])
                    return
                elif data['jobs'][fnid]['state'] == 'FAILED':
                    bar.update(l)
                    click.secho("\nJob failed!", fg="red")
                    rx = json.loads(data['jobs'][fnid]['result'])
                    print("Error", rx['error'])
                    return

    click.secho("Job Execution taking way too long.",fg="yellow")

@cli1.command()
@click.option('--fiuid',help="Your FIU ID received from Darth VDR",default=user_fiuid,callback=checkLoginState,is_eager=True)
@click.option('--configFile',help="The location of configuration file",default='darth-vdr.json',type=click.Path(exists=True,readable=True))
@click.option('--aa',help="The AA ID of the user",prompt='User\'s AA ID')
@click.option('--params',help="The Parameters to send",prompt='Request Parameters')
def job(fiuid,configfile,aa,params):
    with open(configfile, 'r+') as c:
        data = json.load(c)
        if data['id'] == 'new':
            click.echo("Function is not yet created, could not schedule job")
            return
        payload = {
            'fiuId': fiuid,
            'functionId': data['id'],
            'aaId': aa,
            'requestParams': params
        }
        url = base_url + '/createJob'
        r = requests.post(url, headers={}, data = payload)
        if r.status_code != 200 and r.status_code != 202:
            click.secho("Function could not be created!",fg="red")
        else:
            jb = r.json()
            click.secho(f"Job successfully created as {jb['jobId']}")
            jbStatus(jb['jobId'])


@click.group()
def cli2():
    pass

@cli2.command()
def viewlogin():
    click.echo(config.get(default,'fiuid'))




cli = click.CommandCollection(sources=[cli1, cli2])

if __name__ == "__main__":
    cli()

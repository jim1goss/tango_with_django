from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse
# Import the Category model
from rango.models import Category, Page , UserProfile
from rango.forms import CategoryForm, PageForm
from rango.forms import UserForm, UserProfileForm

from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from datetime import datetime
from rango.bing_search import run_query
from django.contrib.auth.models import User

def url_encode(url):
    return url.replace(' ','_')

def url_decode(url):
    return url.replace('_',' ')

def index(request):
    
    context = RequestContext(request)
    cat_list = get_category_list()
    top_cat_list = get_category_list(max_results=5)
    
    page_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories': top_cat_list, 'cat_list' : cat_list, 'pages' : page_list}
    
    #### NEW CODE ####
    if request.session.get('last_visit'):
        # The session has a value for the last visit
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).days > 0:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        # The get returns None, and the session does not have a value for the last visit.
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1

    # Render and return the rendered response back to the user.
    return render_to_response('rango/index.html', context_dict, context)


def get_category_list(max_results=0, starts_with=''):
    
    cat_list = []
    if starts_with:
        cat_list = Category.objects.filter(name__startswith=starts_with)
    else:
        cat_list = Category.objects.all()
        
    if max_results > 0 and len(cat_list) > max_results:
        cat_list = cat_list[:max_results]
        
    # The following two lines are new.
    # We loop through each category returned, and create a URL attribute.
    # This attribute stores an encoded URL (e.g. spaces replaced with underscores).
    for cat in cat_list:
        cat.url = url_encode(cat.name)
    
    return cat_list

def suggest_category(request):
    context = RequestContext(request)

    starts_with = ''
    if request.method == 'GET':
        starts_with = request.GET['suggestion']
    else:
        starts_with = request.POST['suggestion']

    cat_list = get_category_list(8, starts_with)

    return render_to_response('rango/category_list.html', {'cat_list': cat_list }, context)
    
def about(request):
    # Request the context of the request.
    # The context contains information such as the client's machine details, for example.
    context = RequestContext(request)

    # Construct a dictionary to pass to the template engine as its context.
    # Note the key boldmessage is the same as {{ boldmessage }} in the template!
    context_dict = {'boldmessage': "I am from the context about"}
    cat_list = get_category_list()
    context_dict['cat_list'] = cat_list

    count = request.session.get('visits',0)

    context_dict['visit_count'] = count


    # Return a rendered response to send to the client.
    # We make use of the shortcut function to make our lives easier.
    # Note that the first parameter is the template we wish to use.
    return render_to_response('rango/about.html', context_dict, context)


#def about(request):
#    context = RequestContext(request)
#    context_dict = {'boldmessage': "I am from the context about"}
#    return render_to_response('rango/about.html', context_dict, context)

def category(request, category_name_url):
    # Request our context from the request passed to us.
    context = RequestContext(request)

    # Change underscores in the category name to spaces.
    # URLs don't handle spaces well, so we encode them as underscores.
    # We can then simply replace the underscores with spaces again to get the name.
    # category_name = category_name_url.replace('_', ' ')
    print "category_name_url = " + category_name_url
    category_name = url_decode(category_name_url)
    print "category_name = " + category_name
    # Create a context dictionary which we can pass to the template rendering engine.
    # We start by containing the name of the category passed by the user.
    cat_list = get_category_list()
    
    context_dict = {'category_name': category_name, 
                    'category_name_url': category_name_url, 
                    'cat_list' : cat_list}

    result_list = []


    try:
        # Can we find a category with the given name?
        # If we can't, the .get() method raises a DoesNotExist exception.
        # So the .get() method returns one model instance or raises an exception.
        category = Category.objects.get(name__iexact=category_name)

        # Retrieve all of the associated pages.
        # Note that filter returns >= 1 model instance.
        pages = Page.objects.filter(category=category).order_by('-views')

        # Adds our results list to the template context under name pages.
        context_dict['pages'] = pages
        # We also add the category object from the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category
        
    except Category.DoesNotExist:
        # We get here if we didn't find the specified category.
        # Don't do anything - the template displays the "no category" message for us.
        pass

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)
            
    context_dict['result_list'] = result_list

    # Go render the response and return it to the client.
    return render_to_response('rango/category.html', context_dict, context)

@login_required
def add_category(request):
    # Get the context from the request.
    context = RequestContext(request)
    
    context_dict = {}    
    cat_list = get_category_list()
    context_dict['cat_list'] = cat_list

    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            # Save the new category to the database.
            form.save(commit=True)

            # Now call the index() view.
            # The user will be shown the homepage.
            return index(request)
        else:
            # The supplied form contained errors - just print them to the terminal.
            print form.errors
    else:
        # If the request was not a POST, display the form to enter details.
        form = CategoryForm()
        
    context_dict['form'] = form
    
    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render_to_response('rango/add_category.html', context_dict, context)


@login_required
def like_category(request):
    category_id = None
    if request.method == 'GET':
        if 'category_id' in request.GET:
            category_id = request.GET['category_id']
        likes = 0    
        if category_id:
            category = Category.objects.get(id = int(category_id))
            if category:
                likes = category.likes + 1  
                category.save()
               
    return HttpResponse(likes)

    

@login_required
def add_page(request, category_name_url):
    context = RequestContext(request)
    context_dict = {}    
    cat_list = get_category_list()
    context_dict['cat_list'] = cat_list

    category_name = url_decode(category_name_url)
    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            # This time we cannot commit straight away.
            # Not all fields are automatically populated!
            page = form.save(commit=False)

            # Retrieve the associated Category object so we can add it.
            cat = Category.objects.get(name=category_name)
            page.category = cat

            # Also, create a default value for the number of views.
            page.views = 0

            # With this, we can then save our new model instance.
            page.save()

            # Now that the page is saved, display the category instead.
            return category(request, category_name_url)
        else:
            print form.errors
    else:
        form = PageForm()
    
    context_dict['category_name_url'] =  category_name_url
    context_dict['category_name'] =  category_name
    context_dict['form'] = form
    return render_to_response( 'rango/add_page.html', context_dict, context)
    
    
def register(request):
    # Like before, get the request's context.
    context = RequestContext(request)
    
    cat_list = get_category_list()
    context_dict = {}
    context_dict['cat_list'] = cat_list
    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    registered = False

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        # If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            # Save the user's form data to the database.
            user = user_form.save()

            # Now we hash the password with the set_password method.
            # Once hashed, we can update the user object.
            user.set_password(user.password)
            user.save()

            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves, we set commit=False.
            # This delays saving the model until we're ready to avoid integrity problems.
            profile = profile_form.save(commit=False)
            profile.user = user

            # Did the user provide a profile picture?
            # If so, we need to get it from the input form and put it in the UserProfile model.
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            # Now we save the UserProfile model instance.
            profile.save()

            # Update our variable to tell the template registration was successful.
            registered = True

        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            print user_form.errors, profile_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    # Render the template depending on the context.
    context_dict['user_form'] = user_form
    context_dict['profile_form'] = profile_form
    context_dict['registered'] = registered
    return render_to_response(
            'rango/register.html',
            context_dict,
            context)

@login_required
def profile(request):
    # Like before, get the request's context.
    context = RequestContext(request)
    
    cat_list = get_category_list()
    context_dict = {}
    context_dict['cat_list'] = cat_list
    u = User.objects.get(username = request.user)

    try:
        up = UserProfile.objects.get(user=u)
    except:
        up = None
        
    context_dict['user'] = u
    context_dict['userprofile'] = up
    
    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    
    return render_to_response(
            'rango/profile.html',
            context_dict,
            context)

    
    
def user_login(request):
    # Like before, obtain the context for the user's request.
    context = RequestContext(request)
    cat_list = get_category_list()
    context_dict = {}
    context_dict['cat_list'] = cat_list
    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
        username = request.POST['username']
        password = request.POST['password']

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user is not None:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                # We'll send the user back to the homepage.
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your Rango account is disabled.")
        else:
            # Bad login details were provided. So we can't log the user in.
            print "Invalid login details: {0}, {1}".format(username, password)
            return HttpResponse("Invalid login details supplied. for user " + username)

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render_to_response('rango/login.html', context_dict, context)
    
@login_required
def restricted(request):
    # return HttpResponse("Since you're logged in, you can see this text!")
    context = RequestContext(request)
    cat_list = get_category_list()
    context_dict = {}
    context_dict['cat_list'] = cat_list
    return render_to_response('rango/restricted.html', context_dict, context)

from django.contrib.auth import logout

# Use the login_required() decorator to ensure only those logged in can access the view.
@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)

    # Take the user back to the homepage.
    return HttpResponseRedirect('/rango/')

@login_required
def search(request):
    cat_list = get_category_list()
    context_dict = {}
    context_dict['cat_list'] = cat_list
    context = RequestContext(request)
    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)
            
    context_dict['result_list'] = result_list
    
    return render_to_response('rango/search.html', context_dict, context)

@login_required
def track_url(request):
    print "track_url"    
    url = '/rango/'
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            page_id = page_id.strip('/')
            print "page_id = [" + page_id + "]"
            try:
                p = Page.objects.get(id=page_id)
                print "url = " + p.url
                if p:
                    p.views += 1
                    p.save()
                    url = p.url
            except:
                pass
    print "url = " + url                     
    return redirect(url)

@login_required
def auto_add_page(request):
    print "auto_add_page\n\n"
    context = RequestContext(request)
    cat_id = None
    url = None
    title = None
    context_dict = {}
    if request.method == 'GET':
        cat_id = request.GET['category_id']
        url = request.GET['url']
        title = request.GET['title']
        print "cat_id = " +   cat_id + "][" + url + "][" + title + "]\n"
        if cat_id:
            category = Category.objects.get(id=int(cat_id))
            p = Page.objects.get_or_create(category=category, title=title, url=url)
            if p and category:
                redirect_url = '/rango/category/' + category.name + '/'
                print "redirect url = " + redirect_url
                # return redirect("/rango/category/" + category.name + "/")
                return HttpResponse(status=200)
            # pages = Page.objects.filter(category=category).order_by('-views')

            # Adds our results list to the template context under name pages.
            # context_dict['pages'] = pages
    return redirect('rango/')
    #        http://127.0.0.1:8888/rango/category/Aeroplanes/
    # return render_to_response('rango/category.html', context_dict, context)
    # return render_to_response('rango/page_list.html', context_dict, context)

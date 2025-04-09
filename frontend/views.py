from django.shortcuts import render

def frontend_home(request):
    return render(request, "index.html")

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages

from .forms import RegisterForm


def register(request):
    """Allow a new user to create an account and log them in immediately."""

    if request.user.is_authenticated:
        return redirect("uploads:index")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect("uploads:index")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})

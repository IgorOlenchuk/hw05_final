#  импортируем CreateView, чтобы создать ему наследника
from django.views.generic import CreateView

#  функция reverse_lazy позволяет получить URL по параметру "name" функции path()
#  берём, тоже пригодится
from django.urls import reverse_lazy

#  импортируем класс формы, чтобы сослаться на неё во view-классе
from .forms import CreationForm

from django.shortcuts import redirect

class SignUp(CreateView):
    form_class = CreationForm
    success_url = reverse_lazy("signup")
    template_name = "signup.html"

def user_contact(request):
    # проверим, пришёл ли к нам POST-запрос или какой-то другой:
    if request.method == 'POST':
        # создаём объект формы класса ContactForm и передаём в него полученные данные
        form = ContactForm(request.POST)
        # проверяем данные на валидность:
        # ... здесь код валидации ...

        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            sender = form.cleaned_data['sender']
            cc_myself = form.cleaned_data['cc_myself']
            return redirect('/thank-you/')

        # если не сработало условие if form.is_valid() и данные не прошли валидацию
        # сработает следующий блок кода,
        # иначе команда return прервала бы дальнейшее исполнение функции

        # вернём пользователю страницу с HTML-формой и передадим полученный объект формы на страницу, 
        # чтобы вернуть информацию об ошибке

        # заодно автоматически заполним прошедшими валидацию данными все поля, 
        # чтобы не заставлять пользователя второй раз заполнять их
        return render(request, 'contact.html', {'form': form})

    form = ContactForm()
    return render(request, 'contact.html', {'form': form})


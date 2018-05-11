from flask_wtf import FlaskForm as Form
from wtforms import SubmitField, SelectField, TextAreaField, HiddenField


class FormMapGame(Form):
    _id = HiddenField("_id")
    status = SelectField("Статус",
                         choices=[('Не играл', 'Не играл'),
                                  ('Выиграл', 'Выиграл'),
                                  ('Проиграл', 'Проиграл'),
                                  ('Пропустил', 'Пропустил')])

    comment = TextAreaField('Комментарий о карте', render_kw={'rows': 5})
    submit = SubmitField('Сохранить')
    delmap = SubmitField('Удалить карту', render_kw={
        'onclick':
        "return confirm('Вы уверены, что хотите удалить эту карту?');"})

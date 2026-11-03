Phase 1 public UI translations are maintained in the explicit Python catalogue
`catalog/templatetags/library_ui.py`. Category and branding translations are editable
database fields. Django supplies translated admin/auth messages. LocaleMiddleware
and Django set_language handle language cookies without changing/filtering the
catalogue. This folder is reserved for future conventional gettext catalogues.

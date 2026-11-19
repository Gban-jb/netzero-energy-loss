# netzero-energy-loss

**Student 3 — Energy Loss & Financial Impact Analysis**
Part of the [Net Zero Solar Portal](https://netzero-solar-portal.vercel.app)
at Alabama A&M University. Owner: @banjadecodes.

The portal links to this repository from the
[Energy & Cost workstream page](https://netzero-solar-portal.vercel.app/departments/engineering/students/student-3).

---

## Getting your dashboard in here

1. Accept the collaborator invite in your GitHub notifications.
2. Push the Streamlit app:

```sh
git clone https://github.com/Gban-jb/netzero-energy-loss.git
cd netzero-energy-loss
# copy your dashboard files in, then:
git add .
git commit -m "Add the energy loss dashboard"
git push
```

Before you push, make sure `git config user.email` is set to an address
GitHub recognises, or the commit will not be attributed to you:

```sh
git config --global user.email "<id>+<username>@users.noreply.github.com"
```

## What this repository needs

- `app.py` (or whatever the Streamlit entry point is called)
- `requirements.txt` — every package the app imports, so the host can
  install them. `pip freeze > requirements.txt` is a start, but trim it
  to what is actually used.
- Sample input CSVs, so the app runs for someone who has no site data.

## Making the demo live

Streamlit is a running Python server, so it cannot be hosted on the
portal's Vercel project — that serves a static Next.js site. Use
[share.streamlit.io](https://share.streamlit.io): sign in with GitHub,
point it at this repository, name the entry-point file, deploy. It is
free and gives a public URL.

Send that URL to the project manager and it goes on your workstream page
as the live demo link.

Name:           yoink
Version:        0.3.0
Release:        1%{?dist}
Summary:        Local web UI for yt-dlp: downloads, playlists, subscriptions, credential vault
License:        PolyForm-Noncommercial-1.0.0
URL:            https://github.com/jmoraur/Vid-Yoink
# Produced by packaging/make-source-tarball.sh (git archive + pre-built frontend)
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-hatchling
BuildRequires:  python3-pip
BuildRequires:  desktop-file-utils
# %%check runs the (offline) test suite against the real dependencies
BuildRequires:  python3-pytest
BuildRequires:  python3-httpx
BuildRequires:  python3-fastapi
BuildRequires:  python3-uvicorn
BuildRequires:  python3-websockets
BuildRequires:  python3-cryptography
BuildRequires:  yt-dlp

# Python runtime deps are auto-generated from the wheel metadata.
Requires:       hicolor-icon-theme
# the desktop launcher health-checks the server with curl
Requires:       curl
# RPM Fusion's ffmpeg; the default ffmpeg-free lacks the encoders yoink
# needs for merging/extraction/embedding (see README)
Recommends:     ffmpeg
# the desktop launcher opens an app-mode window in Chromium (Chrome or
# Brave work too, if already installed; without any of them it opens a tab
# in the default browser)
Recommends:     chromium
# notify-send: finished/failed downloads and launcher start-up errors
Recommends:     libnotify
# secret-tool: optional unlock of the vault from the desktop keyring
Recommends:     libsecret

%description
Yoink is a local web UI for yt-dlp: downloads with live progress, playlist
subscriptions that fetch only new items, a searchable download archive, and
an encrypted credential vault. Binds to 127.0.0.1 only. Distributed under
the PolyForm Noncommercial 1.0.0 license.

%prep
%autosetup -n %{name}-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files yoink
install -Dm755 scripts/yoink-app %{buildroot}%{_bindir}/yoink-app
install -Dm644 packaging/yoink.desktop %{buildroot}%{_datadir}/applications/yoink.desktop
install -Dm644 packaging/icons/yoink.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/yoink.svg

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/yoink.desktop
%pytest

%files -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/yoink
%{_bindir}/yoink-app
%{_datadir}/applications/yoink.desktop
%{_datadir}/icons/hicolor/scalable/apps/yoink.svg

%changelog
* Wed Nov 11 2026 Jan Moraru <jan@moraru.ch> - 0.3.0-1
- Desktop notification when a download finishes or fails (can be switched off)
- Paste several links at once, one per line
- Subscription filters: upload date, title, skip Shorts, skip live streams
- A bare channel address works as a subscription
- Optional: unlock the vault from the desktop keyring at launch
- Without Chromium/Chrome/Brave the launcher opens a tab in the default
  browser; the server stops itself when the last tab closes

* Wed Nov 11 2026 Jan Moraru <jan@moraru.ch> - 0.2.0-1
- Failed downloads are reported as failed (were saved as finished)
- Requests from other websites are refused (Host and Origin check)
- The queue survives closing the app; unfinished downloads resume
- Subscription checks skip items already queued, give up after 3 failures,
  and read up to 5000 entries
- Launcher also finds Chrome and Brave
- New interface: one Downloads screen, three sections, thumbnails,
  plain-language errors, open folder, retry failed, clear list

* Tue Jul 21 2026 Jan Moraru <jan@moraru.ch> - 0.1.0-1
- Initial package

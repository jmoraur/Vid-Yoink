Name:           yoink
Version:        0.1.0
Release:        1%{?dist}
Summary:        Local web UI for yt-dlp: downloads, playlists, subscriptions, credential vault
License:        PolyForm-Noncommercial-1.0.0
URL:            https://github.com/jmorarur/Vid-Yoink
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
# the desktop launcher opens a Chromium app-mode window and reports
# startup errors via desktop notifications
Recommends:     chromium
Recommends:     libnotify

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
* Tue Jul 21 2026 Jan Moraru <jan@moraru.ch> - 0.1.0-1
- Initial package

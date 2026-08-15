import time
import os
import comtypes

class AudioMonitor:
    def __init__(self, threshold=0.01, ignore_apps=None):
        """
        :param threshold: Peak volume threshold (0.0 to 1.0) above which audio is considered 'playing'
        :param ignore_apps: List of executable names (lowercased) to ignore (e.g., ['spotify.exe'])
        """
        self.threshold = threshold
        self.ignore_apps = [app.lower() for app in (ignore_apps or ['spotify.exe'])]
        self.ignore_apps.extend(["python.exe", "pythonw.exe", "py.exe"])

    def set_ignore_apps(self, ignore_apps):
        self.ignore_apps = [app.lower() for app in ignore_apps]
        self.ignore_apps.extend(["python.exe", "pythonw.exe", "py.exe"])

    def get_other_audio_sessions(self):
        """
        Returns (max_non_spotify_peak, list_of_active_sources)
        """
        try:
            comtypes.CoInitialize()
        except Exception:
            pass

        active_sources = []
        max_non_spotify_peak = 0.0

        try:
            from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process:
                    proc_name = session.Process.name().lower()
                    if proc_name in self.ignore_apps:
                        continue

                    # Query peak meter for this session
                    meter = session._ctl.QueryInterface(IAudioMeterInformation)
                    peak = meter.GetPeakValue()

                    if peak > max_non_spotify_peak:
                        max_non_spotify_peak = peak

                    if peak >= self.threshold:
                        active_sources.append({
                            'pid': session.ProcessId,
                            'name': session.Process.name(),
                            'peak': peak
                        })
        except Exception as e:
            pass

        return max_non_spotify_peak, active_sources

if __name__ == '__main__':
    monitor = AudioMonitor(threshold=0.01)
    print("Testing Audio Monitor... Play some audio in browser or app (not Spotify).")
    for _ in range(10):
        peak, sources = monitor.get_other_audio_sessions()
        if sources:
            print(f"[AUDIO DETECTED] Peak: {peak:.4f} | Sources: {[s['name'] for s in sources]}")
        else:
            print(f"[QUIET] Max Non-Spotify Peak: {peak:.4f}")
        time.sleep(0.5)

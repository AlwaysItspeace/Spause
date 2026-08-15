import asyncio
import winsdk.windows.media.control as wmc

class SpotifyControllerSMTC:
    """
    Windows System Media Transport Controls (SMTC) Controller.
    Directly targets the Spotify Windows desktop session.
    """
    def __init__(self):
        pass

    async def _get_spotify_session(self):
        try:
            manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
            sessions = manager.get_sessions()
            for session in sessions:
                if "spotify" in session.source_app_user_model_id.lower():
                    return session
        except Exception:
            pass
        return None

    def pause(self):
        """Pause Spotify playback explicitly."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            session = loop.run_until_complete(self._get_spotify_session())
            if session:
                res = loop.run_until_complete(session.try_pause_async())
                loop.close()
                return res
            loop.close()
        except Exception as e:
            print(f"SMTC Pause error: {e}")
        return False

    def play(self):
        """Resume Spotify playback explicitly."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            session = loop.run_until_complete(self._get_spotify_session())
            if session:
                res = loop.run_until_complete(session.try_play_async())
                loop.close()
                return res
            loop.close()
        except Exception as e:
            print(f"SMTC Play error: {e}")
        return False

class SpotifyController:
    """
    Unified Spotify Controller with explicit SMTC targetting.
    """
    def __init__(self, mode='smtc', client_id='', client_secret=''):
        self.mode = mode
        self.smtc = SpotifyControllerSMTC()

    def pause(self):
        return self.smtc.pause()

    def play(self):
        return self.smtc.play()

if __name__ == '__main__':
    ctrl = SpotifyController()
    print("Testing SMTC pause...")
    ctrl.pause()

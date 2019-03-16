from Youtube import YoutubeItem

try:
    ytItem = YoutubeItem("https://www.youtube.com/watch?v=kJQP7kiw5Fk", audioformat="audio/mp4", videoformat="video/mp4")
    ytAudioAvailable = ytItem.getAudioList()
    ytVideoAvailable = ytItem.getVideoList()

    ytAudio = ytAudioAvailable[0]
    ytAudio.download(path="music/")

    ytVideo = ytVideoAvailable[0]
    ytVideo.download(path="video/")
except Exception as e:
    print(e)
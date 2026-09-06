import requests

tex = r"""
\documentclass{article}
\begin{document}
Hello world!
\end{document}
"""

res = requests.post("https://latexonline.cc/compile", data={"text": tex})
if res.status_code == 200:
    print("Success! Size:", len(res.content))
else:
    print("Failed:", res.status_code, res.text)

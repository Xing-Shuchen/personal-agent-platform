let accessLost = false;

/** An expired portal observer cookie must remove already-rendered private state. */
export function requireViewer(response: Response): Response {
  if (response.status === 401 || response.status === 403) {
    if (!accessLost) {
      accessLost = true;
      const notice = document.createElement('main');
      const title = document.createElement('h1');
      title.textContent = '观察权限已失效';
      notice.append(title);
      document.body.replaceChildren(notice);
      window.location.replace('/');
    }
    throw new Error('viewer access lost');
  }
  if (accessLost) throw new Error('viewer access lost');
  return response;
}

using UnityEngine;

public class CameraAutoFit : MonoBehaviour
{
    // Actual world-space extents that must be visible
    // Main Canvas SGT in scene is 3000x1500 at scale 0.00625 = 18.75 x 9.375 world units
    public float targetWorldWidth = 19f;
    public float targetWorldHeight = 9.5f;

    private Camera cam;
    private int lastScreenWidth;
    private int lastScreenHeight;

    void Start()
    {
        cam = GetComponent<Camera>();
        AdjustCamera();
    }

    void Update()
    {
        if (Screen.width != lastScreenWidth || Screen.height != lastScreenHeight)
        {
            AdjustCamera();
        }
    }

    void AdjustCamera()
    {
        if (cam == null || !cam.orthographic) return;

        lastScreenWidth = Screen.width;
        lastScreenHeight = Screen.height;

        float aspectRatio = (float)Screen.width / Screen.height;
        // Ortho size needed to fit width
        float sizeForWidth = (targetWorldWidth / 2f) / aspectRatio;
        // Ortho size needed to fit height
        float sizeForHeight = targetWorldHeight / 2f;
        // Use whichever is larger to ensure both dimensions fit
        float newSize = Mathf.Max(sizeForWidth, sizeForHeight);
        cam.orthographicSize = newSize;
        Debug.Log("CameraAutoFit: screen=" + Screen.width + "x" + Screen.height +
                  " aspect=" + aspectRatio + " orthoSize=" + newSize);
    }
}

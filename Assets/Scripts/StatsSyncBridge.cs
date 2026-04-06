using System.Runtime.InteropServices;
using UnityEngine;

public static class StatsSyncBridge
{
#if UNITY_WEBGL && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern string JS_GetPlayerName();

    [DllImport("__Internal")]
    private static extern int JS_GetMaxScore(string username, string config);

    [DllImport("__Internal")]
    private static extern int JS_PostScore(string username, string config, int mana);

    [DllImport("__Internal")]
    private static extern void JS_DeleteScores(string username);
#endif

    public static string GetPlayerName()
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        try { return JS_GetPlayerName(); }
        catch (System.Exception e) { Debug.LogError("GetPlayerName: " + e.Message); }
#endif
        return "default";
    }

    public static int GetMaxScore(string username, string config)
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        try { return JS_GetMaxScore(username, config); }
        catch (System.Exception e) { Debug.LogError("GetMaxScore: " + e.Message); }
#endif
        return 0;
    }

    public static int PostScore(string username, string config, int mana)
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        try { return JS_PostScore(username, config, mana); }
        catch (System.Exception e) { Debug.LogError("PostScore: " + e.Message); }
#endif
        return mana;
    }

    public static void DeleteScores(string username)
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        try { JS_DeleteScores(username); }
        catch (System.Exception e) { Debug.LogError("DeleteScores: " + e.Message); }
#endif
    }
}

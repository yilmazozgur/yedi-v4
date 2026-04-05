using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;

public static class StatsSyncBridge
{
#if UNITY_WEBGL && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern void JS_SaveStats(string json);

    [DllImport("__Internal")]
    private static extern string JS_LoadStats();

    [DllImport("__Internal")]
    private static extern void JS_DeleteStats();
#endif

    public static void SaveToServer(Dictionary<string, List<float>> statsDictionary)
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        try
        {
            string json = DictToJson(statsDictionary);
            JS_SaveStats(json);
        }
        catch (System.Exception e)
        {
            Debug.LogError("StatsSyncBridge.SaveToServer: " + e.Message);
        }
#endif
    }

    public static Dictionary<string, List<float>> LoadFromServer()
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        try
        {
            string json = JS_LoadStats();
            if (!string.IsNullOrEmpty(json) && json != "{}")
            {
                return JsonToDict(json);
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError("StatsSyncBridge.LoadFromServer: " + e.Message);
        }
#endif
        return null;
    }

    public static void DeleteOnServer()
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        try
        {
            JS_DeleteStats();
        }
        catch (System.Exception e)
        {
            Debug.LogError("StatsSyncBridge.DeleteOnServer: " + e.Message);
        }
#endif
    }

    // Minimal JSON serialization — avoids needing Newtonsoft/JsonUtility for Dictionary
    private static string DictToJson(Dictionary<string, List<float>> dict)
    {
        var sb = new System.Text.StringBuilder();
        sb.Append('{');
        bool first = true;
        foreach (var kvp in dict)
        {
            if (!first) sb.Append(',');
            first = false;
            sb.Append('"');
            sb.Append(EscapeJson(kvp.Key));
            sb.Append("\":[");
            for (int i = 0; i < kvp.Value.Count; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append(kvp.Value[i].ToString(System.Globalization.CultureInfo.InvariantCulture));
            }
            sb.Append(']');
        }
        sb.Append('}');
        return sb.ToString();
    }

    private static Dictionary<string, List<float>> JsonToDict(string json)
    {
        var dict = new Dictionary<string, List<float>>();
        // Simple JSON parser for {"key":[1.0,2.0],...} format
        int i = 0;
        if (i >= json.Length || json[i] != '{') return dict;
        i++; // skip {

        while (i < json.Length && json[i] != '}')
        {
            // Skip whitespace and commas
            while (i < json.Length && (json[i] == ',' || json[i] == ' ' || json[i] == '\n' || json[i] == '\r' || json[i] == '\t'))
                i++;

            if (i >= json.Length || json[i] == '}') break;

            // Parse key
            if (json[i] != '"') break;
            i++; // skip opening "
            int keyStart = i;
            while (i < json.Length && json[i] != '"')
            {
                if (json[i] == '\\') i++; // skip escaped char
                i++;
            }
            string key = json.Substring(keyStart, i - keyStart);
            i++; // skip closing "

            // Skip : and whitespace
            while (i < json.Length && (json[i] == ':' || json[i] == ' '))
                i++;

            // Parse array
            var list = new List<float>();
            if (i < json.Length && json[i] == '[')
            {
                i++; // skip [
                while (i < json.Length && json[i] != ']')
                {
                    while (i < json.Length && (json[i] == ',' || json[i] == ' '))
                        i++;
                    if (i >= json.Length || json[i] == ']') break;

                    int numStart = i;
                    while (i < json.Length && json[i] != ',' && json[i] != ']' && json[i] != ' ')
                        i++;
                    string numStr = json.Substring(numStart, i - numStart);
                    if (float.TryParse(numStr, System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture, out float val))
                    {
                        list.Add(val);
                    }
                }
                if (i < json.Length && json[i] == ']') i++; // skip ]
            }

            dict[key] = list;
        }

        return dict;
    }

    private static string EscapeJson(string s)
    {
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }
}

using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.EventSystems;

namespace ChartUtil
{
    public class ChartPointerHandler : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler, IPointerDownHandler
    {
        Camera eventCam;
        RectTransform rectTransform;
        bool isMouseOver = false;

        public UnityAction onPointerEnter;
        public UnityAction onPointerExit;
        public UnityAction onPointerDown;
        public UnityAction onPointerHover;

        private void Awake()
        {
            rectTransform = GetComponent<RectTransform>();
        }

        private void Update()
        {
            if (isMouseOver && onPointerHover != null)
            {
                onPointerHover.Invoke();
            }
        }

        public void GetMousePos(out Vector2 mousePos)
        {
            RectTransformUtility.ScreenPointToLocalPointInRectangle(rectTransform, Input.mousePosition, eventCam, out mousePos);
        }

        public void OnPointerDown(PointerEventData eventData)
        {
            eventCam = eventData.pressEventCamera;
            if (onPointerDown != null) onPointerDown.Invoke();
        }

        public void OnPointerEnter(PointerEventData eventData)
        {
            isMouseOver = true;
            eventCam = eventData.enterEventCamera;
            if (onPointerEnter != null) onPointerEnter.Invoke();
        }

        public void OnPointerExit(PointerEventData eventData)
        {
            isMouseOver = false;
            if (onPointerExit != null) onPointerExit.Invoke();
        }
    }
}
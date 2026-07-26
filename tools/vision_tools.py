"""
Vision Tools
"""

from services.vision_service import (

    analyze_image,

    analyze_chart,

    compare_images

)





VISION_TOOLS = {



"image_analysis":

{


"name":

"image_analysis",



"description":

"Analyze an image and explain its content",



"function":

analyze_image

},





"chart_analysis":

{


"name":

"chart_analysis",



"description":

"Read and explain charts and graphs",



"function":

analyze_chart

},





"image_compare":

{


"name":

"image_compare",



"description":

"Compare two images",



"function":

compare_images

}



}







def get_vision_tools():


    return VISION_TOOLS
# kotlinx-serialization 需要保留 @Serializable 信息
-keep,includedescriptorclasses class app.ling.client.**$$serializer { *; }
-keepclassmembers class app.ling.client.** {
    *** Companion;
}
-keepclasseswithmembers class app.ling.client.** {
    kotlinx.serialization.KSerializer serializer(...);
}
